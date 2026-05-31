"""
PDF Export Utilities for Timetable Scheduling System

Supports:
- Batch-wise timetable export (all classes or a single class)
- Teacher-wise timetable export (all teachers or a single teacher)
- A4 printable layout with school header
- Multi-tenant: every query is scoped to the timetable's organization
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from models import db, Timetable, TimetableSlot, Batch, Teacher, Subject, SchoolConfig

# Canonical week order; we slice this to the configured number of working days
# instead of hardcoding Monday–Friday.
WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class TimetablePDFExporter:
    """Generate PDF exports for a timetable, scoped to one organization."""

    def __init__(self, timetable_id, organization_id=None, school_name="School Name", logo_path=None):
        self.timetable = Timetable.query.get(timetable_id)
        if not self.timetable:
            raise ValueError(f"Timetable {timetable_id} not found")

        # Prefer the explicit org id; fall back to the timetable's own org so a
        # PDF can never mix data from another tenant.
        self.organization_id = organization_id or self.timetable.organization_id

        self.school_name = school_name or self.timetable.school_name or "School Name"
        self.logo_path = logo_path or self.timetable.school_logo_path
        self.school_config = self._scoped(SchoolConfig).first()

        # Cache lookups so we don't issue a query per slot.
        self._teacher_by_id = {t.id: t for t in self._scoped(Teacher).all()}
        self._subject_by_id = {s.id: s for s in self._scoped(Subject).all()}
        self._batch_by_id = {b.id: b for b in self._scoped(Batch).all()}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _scoped(self, model):
        """Return a query for `model` filtered to this organization."""
        q = model.query
        if self.organization_id is not None:
            q = q.filter_by(organization_id=self.organization_id)
        return q

    def _days(self):
        """Working days for this school, derived from config (default 5)."""
        working = self.school_config.working_days if self.school_config else 5
        working = max(1, min(working or 5, len(WEEK_DAYS)))
        return WEEK_DAYS[:working]

    def _full_layout(self):
        """Full school-day period rows (number/start/end/is_lunch)."""
        from period_utils import build_layout
        if not self.school_config:
            return [{"number": i, "start": "", "end": "", "is_lunch": False} for i in range(1, 7)]
        return build_layout(self.school_config)

    def _batch_layout(self, batch):
        """Period rows for one class, capped to that class's day length."""
        from period_utils import build_layout, batch_period_count
        if not self.school_config:
            return self._full_layout()
        return build_layout(self.school_config, count=batch_period_count(batch, self.school_config))

    def _row_label(self, row):
        """'Period N\\n(HH:MM)' label for a layout row."""
        if row.get("start"):
            return f"Period {row['number']}\n({row['start']})"
        return f"Period {row['number']}"

    def _batch_label(self, batch):
        if not batch:
            return "Unknown"
        return f"Grade {batch.grade} - Section {batch.section}"

    def _get_header(self):
        """Create PDF header with school name and date."""
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=22,
            textColor=colors.HexColor('#1a3a52'), spaceAfter=4, alignment=1,
        )
        story.append(Paragraph(self.school_name, title_style))

        subtitle_style = ParagraphStyle(
            'CustomSubtitle', parent=styles['Heading2'], fontSize=13,
            textColor=colors.HexColor('#4a7ba7'), spaceAfter=4, alignment=1,
        )
        story.append(Paragraph(f"Timetable: {self.timetable.name}", subtitle_style))

        date_style = ParagraphStyle(
            'DateStyle', parent=styles['Normal'], fontSize=9,
            textColor=colors.grey, spaceAfter=10, alignment=1,
        )
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%d %b %Y at %H:%M')}", date_style,
        ))
        story.append(Spacer(1, 0.15 * inch))
        return story

    # ------------------------------------------------------------------
    # Batch-wise
    # ------------------------------------------------------------------
    def generate_batch_wise_pdf(self, batch_id=None):
        """PDF with a grid per class. If batch_id is given, only that class."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        story = []
        styles = getSampleStyleSheet()

        if batch_id is not None:
            batch = self._batch_by_id.get(batch_id)
            batches = [batch] if batch else []
        else:
            batches = sorted(self._batch_by_id.values(), key=lambda b: (str(b.grade), str(b.section)))

        if not batches:
            story.extend(self._get_header())
            story.append(Paragraph("No class found for this timetable.", styles['Normal']))
            doc.build(story)
            buffer.seek(0)
            return buffer

        for idx, batch in enumerate(batches):
            if idx > 0:
                story.append(PageBreak())
            story.extend(self._get_header())

            # Class teacher = teacher whose class_teacher_batch_id matches.
            class_teacher = next(
                (t for t in self._teacher_by_id.values() if t.class_teacher_batch_id == batch.id),
                None,
            )
            meta = f"Students: {batch.student_count or 0}"
            if class_teacher:
                code = f" ({class_teacher.teacher_code})" if class_teacher.teacher_code else ""
                meta += f"  •  Class Teacher: {class_teacher.name}{code}"

            story.append(Paragraph(self._batch_label(batch), self._block_title('#1a3a52')))
            story.append(Paragraph(meta, self._meta_style()))

            slots = TimetableSlot.query.filter_by(batch_id=batch.id, timetable_id=self.timetable.id).all()
            table_data = self._build_batch_table(slots, batch)
            story.append(self._make_table(table_data))
            story.append(Spacer(1, 0.25 * inch))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _build_batch_table(self, slots, batch):
        days = self._days()
        layout = self._batch_layout(batch)
        slot_map = {(s.day, s.period_number): s for s in slots}

        table_data = [["Period"] + days]
        for row_def in layout:
            period_num = row_def["number"]
            row = [self._row_label(row_def)]
            for day in days:
                slot = slot_map.get((day, period_num))
                if row_def["is_lunch"] or (slot and slot.is_lunch):
                    row.append("LUNCH")
                elif slot and slot.teacher_id:
                    subject = self._subject_by_id.get(slot.subject_id)
                    teacher = self._teacher_by_id.get(slot.teacher_id)
                    subject_name = subject.name if subject else "---"
                    teacher_name = teacher.name.split()[0] if teacher else "---"
                    row.append(f"{subject_name}\n({teacher_name})")
                else:
                    row.append("")
            table_data.append(row)
        return table_data

    # ------------------------------------------------------------------
    # Teacher-wise
    # ------------------------------------------------------------------
    def generate_teacher_wise_pdf(self, teacher_id=None):
        """PDF with a grid per teacher. If teacher_id is given, only that one."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        story = []
        styles = getSampleStyleSheet()

        if teacher_id is not None:
            teacher = self._teacher_by_id.get(teacher_id)
            teachers = [teacher] if teacher else []
        else:
            teachers = sorted(self._teacher_by_id.values(), key=lambda t: t.name or "")

        if not teachers:
            story.extend(self._get_header())
            story.append(Paragraph("No teacher found for this timetable.", styles['Normal']))
            doc.build(story)
            buffer.seek(0)
            return buffer

        for idx, teacher in enumerate(teachers):
            if idx > 0:
                story.append(PageBreak())
            story.extend(self._get_header())

            subject_names = ", ".join(
                self._subject_by_id[s].name
                for s in (teacher.subject_ids or [])
                if s in self._subject_by_id
            ) or "—"
            code = f"{teacher.teacher_code} • " if teacher.teacher_code else ""

            story.append(Paragraph(teacher.name, self._block_title('#4a7ba7')))
            story.append(Paragraph(f"{code}Subjects: {subject_names}", self._meta_style()))

            slots = TimetableSlot.query.filter_by(teacher_id=teacher.id, timetable_id=self.timetable.id).all()
            table_data = self._build_teacher_table(slots)
            story.append(self._make_table(table_data))
            story.append(Spacer(1, 0.25 * inch))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _build_teacher_table(self, slots):
        days = self._days()
        layout = self._full_layout()
        slot_map = {(s.day, s.period_number): s for s in slots}

        table_data = [["Period"] + days]
        for row_def in layout:
            period_num = row_def["number"]
            row = [self._row_label(row_def)]
            for day in days:
                slot = slot_map.get((day, period_num))
                if row_def["is_lunch"] or (slot and slot.is_lunch):
                    row.append("LUNCH")
                elif slot and slot.batch_id and not slot.is_lunch:
                    subject = self._subject_by_id.get(slot.subject_id)
                    batch = self._batch_by_id.get(slot.batch_id)
                    subject_name = subject.name if subject else "---"
                    batch_name = f"Grade {batch.grade}-{batch.section}" if batch else "---"
                    row.append(f"{subject_name}\n({batch_name})")
                else:
                    row.append("")
            table_data.append(row)
        return table_data

    # ------------------------------------------------------------------
    # Shared styling
    # ------------------------------------------------------------------
    def _block_title(self, hex_color):
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'BlockTitle', parent=styles['Heading2'], fontSize=12,
            textColor=colors.white, backColor=colors.HexColor(hex_color),
            spaceAfter=2, alignment=1,
        )

    def _meta_style(self):
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'Meta', parent=styles['Normal'], fontSize=9,
            textColor=colors.HexColor('#333333'), spaceAfter=8, alignment=1,
        )

    def _make_table(self, table_data):
        days_count = len(table_data[0]) - 1 if table_data else 5
        table = Table(table_data, colWidths=[1.0 * inch] + [(9.0 / max(days_count, 1)) * inch] * days_count)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a52')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        return table


def export_batch_timetable(timetable_id, organization_id=None, school_name="School", batch_id=None):
    """Export timetable as PDF (batch-wise; one class if batch_id given)."""
    exporter = TimetablePDFExporter(timetable_id, organization_id=organization_id, school_name=school_name)
    return exporter.generate_batch_wise_pdf(batch_id=batch_id)


def export_teacher_timetable(timetable_id, organization_id=None, school_name="School", teacher_id=None):
    """Export timetable as PDF (teacher-wise; one teacher if teacher_id given)."""
    exporter = TimetablePDFExporter(timetable_id, organization_id=organization_id, school_name=school_name)
    return exporter.generate_teacher_wise_pdf(teacher_id=teacher_id)
