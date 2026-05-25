"""
PDF Export Utilities for Timetable Scheduling System

Supports:
- Batch-wise timetable export
- Teacher-wise timetable export
- Full school timetable
- A4 printable layout with school header
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from models import db, Timetable, TimetableSlot, Batch, Teacher, Subject, SchoolConfig


class TimetablePDFExporter:
    """Generate PDF exports for timetables"""
    
    def __init__(self, timetable_id, school_name="School Name", logo_path=None):
        self.timetable = Timetable.query.get(timetable_id)
        if not self.timetable:
            raise ValueError(f"Timetable {timetable_id} not found")
        
        self.school_name = school_name or self.timetable.school_name or "School Name"
        self.logo_path = logo_path or self.timetable.school_logo_path
        self.school_config = SchoolConfig.query.first()
    
    def _get_header(self, doc):
        """Create PDF header with school name and date"""
        styles = getSampleStyleSheet()
        story = []
        
        # School name
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a3a52'),
            spaceAfter=6,
            alignment=1  # Center
        )
        story.append(Paragraph(self.school_name, title_style))
        
        # Timetable name
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4a7ba7'),
            spaceAfter=6,
            alignment=1
        )
        story.append(Paragraph(f"Timetable: {self.timetable.name}", subtitle_style))
        
        # Generated date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=12,
            alignment=1
        )
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}", date_style))
        
        story.append(Spacer(1, 0.2 * inch))
        return story
    
    def _get_time_periods(self):
        """Get list of periods with times"""
        periods = []
        if self.school_config:
            # Calculate period times
            start_hour, start_min = map(int, self.school_config.start_time.split(':'))
            period_duration = self.school_config.period_duration
            
            for i in range(1, self.school_config.periods_per_day + 1):
                total_minutes = (start_hour * 60 + start_min) + (i - 1) * period_duration
                hours = total_minutes // 60
                mins = total_minutes % 60
                time_str = f"{hours:02d}:{mins:02d}"
                periods.append(f"Period {i}\n({time_str})")
        else:
            periods = [f"Period {i}" for i in range(1, 7)]
        return periods
    
    def generate_batch_wise_pdf(self):
        """Generate PDF with timetable for each batch"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Get all batches with slots
        batches = Batch.query.all()
        
        for batch_idx, batch in enumerate(batches):
            # Add header only on first page
            if batch_idx == 0:
                story.extend(self._get_header(doc))
            else:
                story.append(PageBreak())
                story.extend(self._get_header(doc))
            
            # Batch title
            styles = getSampleStyleSheet()
            batch_title = ParagraphStyle(
                'BatchTitle',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.white,
                backColor=colors.HexColor('#1a3a52'),
                spaceAfter=10,
                alignment=1
            )
            story.append(Paragraph(f"Grade {batch.grade} - Section {batch.section}", batch_title))
            
            # Build table
            slots_data = TimetableSlot.query.filter_by(batch_id=batch.id, timetable_id=self.timetable.id).all()
            table_data = self._build_batch_table(batch, slots_data)
            
            if table_data:
                table = Table(table_data, colWidths=[0.9*inch] + [1.1*inch] * 5)
                table.setStyle(self._get_table_style())
                story.append(table)
            else:
                story.append(Paragraph("No timetable data found for this batch.", styles['Normal']))
            
            story.append(Spacer(1, 0.3 * inch))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_teacher_wise_pdf(self):
        """Generate PDF with timetable for each teacher"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Get all teachers with slots
        teachers = Teacher.query.all()
        
        for teacher_idx, teacher in enumerate(teachers):
            # Add header
            if teacher_idx == 0:
                story.extend(self._get_header(doc))
            else:
                story.append(PageBreak())
                story.extend(self._get_header(doc))
            
            # Teacher title
            styles = getSampleStyleSheet()
            teacher_title = ParagraphStyle(
                'TeacherTitle',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.white,
                backColor=colors.HexColor('#4a7ba7'),
                spaceAfter=10,
                alignment=1
            )
            story.append(Paragraph(f"{teacher.name} - {', '.join([Subject.query.get(s).name if s else '' for s in teacher.subject_ids or []])}", teacher_title))
            
            # Build table
            slots_data = TimetableSlot.query.filter_by(teacher_id=teacher.id, timetable_id=self.timetable.id).all()
            table_data = self._build_teacher_table(teacher, slots_data)
            
            if table_data:
                table = Table(table_data, colWidths=[0.9*inch] + [1.1*inch] * 5)
                table.setStyle(self._get_table_style())
                story.append(table)
            else:
                story.append(Paragraph("No timetable data found for this teacher.", styles['Normal']))
            
            story.append(Spacer(1, 0.3 * inch))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _build_batch_table(self, batch, slots):
        """Build batch timetable data for PDF table"""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = self._get_time_periods()
        
        # Header row
        table_data = [["Period"] + days]
        
        # Group slots by period
        for period_num in range(1, (self.school_config.periods_per_day if self.school_config else 6) + 1):
            row = [periods[period_num - 1]]
            
            for day in days:
                slot = next((s for s in slots if s.day == day and s.period_number == period_num), None)
                
                if slot and slot.is_lunch:
                    cell_text = "LUNCH"
                elif slot:
                    subject = Subject.query.get(slot.subject_id)
                    teacher = Teacher.query.get(slot.teacher_id)
                    subject_name = subject.name if subject else "---"
                    teacher_name = teacher.name.split()[0] if teacher else "---"
                    cell_text = f"{subject_name}\n({teacher_name})"
                else:
                    cell_text = ""
                
                row.append(cell_text)
            
            table_data.append(row)
        
        return table_data
    
    def _build_teacher_table(self, teacher, slots):
        """Build teacher timetable data for PDF table"""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = self._get_time_periods()
        
        # Header row
        table_data = [["Period"] + days]
        
        # Group slots by period
        for period_num in range(1, (self.school_config.periods_per_day if self.school_config else 6) + 1):
            row = [periods[period_num - 1]]
            
            for day in days:
                slot = next((s for s in slots if s.day == day and s.period_number == period_num), None)
                
                if slot and slot.is_lunch:
                    cell_text = "LUNCH"
                elif slot:
                    subject = Subject.query.get(slot.subject_id)
                    batch = Batch.query.get(slot.batch_id)
                    subject_name = subject.name if subject else "---"
                    batch_name = f"Grade {batch.grade}-{batch.section}" if batch else "---"
                    cell_text = f"{subject_name}\n({batch_name})"
                else:
                    cell_text = ""
                
                row.append(cell_text)
            
            table_data.append(row)
        
        return table_data
    
    def _get_table_style(self):
        """Get table styling"""
        return TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a52')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Data row styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            
            # Borders
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ])


def export_batch_timetable(timetable_id, school_name="School"):
    """Export timetable as PDF (batch-wise)"""
    exporter = TimetablePDFExporter(timetable_id, school_name)
    return exporter.generate_batch_wise_pdf()


def export_teacher_timetable(timetable_id, school_name="School"):
    """Export timetable as PDF (teacher-wise)"""
    exporter = TimetablePDFExporter(timetable_id, school_name)
    return exporter.generate_teacher_wise_pdf()
