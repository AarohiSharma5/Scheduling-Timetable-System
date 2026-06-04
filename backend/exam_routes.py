"""
Exams / Gradebook / Report-card API.

Endpoints (under /api/exams, all tenant-scoped):
  GET    /                       List exams (students see published only)
  POST   /                       Create exam            (admin/principal)
  PUT    /<id>                    Update exam            (admin/principal)
  DELETE /<id>                    Delete exam            (admin/principal)
  POST   /<id>/publish           Publish results        (admin/principal)
  GET    /<id>/marksheet         Roster + marks for a class+subject (entry grid)
  POST   /<id>/marks             Bulk upsert marks for a class+subject
  GET    /<id>/results           Class report card (students x subjects)
  GET    /student/<student_id>   A student's results (own only, published)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from models import (
    db, Exam, Mark, Student, Batch, Subject, Teacher, grade_for_percentage,
)
from jwt_utils import token_required, role_required

exam_bp = Blueprint("exams", __name__, url_prefix="/api/exams")


# ---------------------------------------------------------------------------
# Helpers (local to avoid a circular import with routes.py)
# ---------------------------------------------------------------------------

def _org_id():
    user = getattr(request, "user", None)
    return user.get("organization_id") if user else None


def _role():
    return (getattr(request, "user", {}) or {}).get("role")


def _is_admin_principal():
    return _role() in ("admin", "principal")


def _acting_teacher():
    user = getattr(request, "user", None)
    if not user or user.get("role") != "teacher":
        return None
    return Teacher.query.filter_by(
        user_id=user.get("user_id"), organization_id=_org_id()
    ).first()


def _allowed_batch_ids(teacher):
    ids = set(teacher.assigned_batch_ids or [])
    if teacher.class_teacher_batch_id:
        ids.add(teacher.class_teacher_batch_id)
    return ids


def _can_access_batch(batch):
    if batch is None or batch.organization_id != _org_id():
        return False
    if _is_admin_principal():
        return True
    teacher = _acting_teacher()
    return bool(teacher) and batch.id in _allowed_batch_ids(teacher)


def _roster(batch):
    students = Student.query.filter(
        Student.organization_id == _org_id(),
        Student.class_grade == str(batch.grade),
        Student.section == batch.section,
        Student.status == "Active",
    ).all()
    students.sort(key=lambda s: (s.roll_no if s.roll_no is not None else 9999,
                                 (s.first_name or "").lower()))
    return students


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _owned_exam(exam_id):
    return Exam.query.filter_by(id=exam_id, organization_id=_org_id()).first()


# ---------------------------------------------------------------------------
# Meta (classes the caller may grade + subject names) for selectors
# ---------------------------------------------------------------------------

@exam_bp.route("/meta", methods=["GET"])
@token_required
def exam_meta():
    org_id = _org_id()
    batches = Batch.query.filter_by(organization_id=org_id).all()
    if not _is_admin_principal():
        teacher = _acting_teacher()
        if not teacher:
            return jsonify({"error": "Only staff can grade exams"}), 403
        allowed = _allowed_batch_ids(teacher)
        batches = [b for b in batches if b.id in allowed]
    batches.sort(key=lambda b: (str(b.grade), b.section))

    subjects = Subject.query.filter_by(organization_id=org_id).order_by(Subject.name).all()
    return jsonify({
        "classes": [{
            "batch_id": b.id,
            "label": f"Grade {b.grade}-{b.section}",
            "subject_ids": b.subject_ids or [],
        } for b in batches],
        "subjects": [{"id": s.id, "name": s.name} for s in subjects],
    }), 200


# ---------------------------------------------------------------------------
# Exam CRUD
# ---------------------------------------------------------------------------

@exam_bp.route("", methods=["GET"])
@token_required
def list_exams():
    q = Exam.query.filter_by(organization_id=_org_id())
    # Students only ever see published exams.
    if _role() == "student":
        q = q.filter_by(status="published")
    exams = q.order_by(Exam.created_at.desc()).all()
    return jsonify([e.to_dict() for e in exams]), 200


@exam_bp.route("", methods=["POST"])
@role_required("admin", "principal")
def create_exam():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Exam name is required"}), 400
    exam = Exam(
        organization_id=_org_id(),
        name=name,
        term=(data.get("term") or None),
        exam_type=(data.get("exam_type") or "other"),
        max_marks=int(data.get("max_marks") or 100),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        status="draft",
    )
    db.session.add(exam)
    db.session.commit()
    return jsonify(exam.to_dict()), 201


@exam_bp.route("/<int:exam_id>", methods=["PUT"])
@role_required("admin", "principal")
def update_exam(exam_id):
    exam = _owned_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        exam.name = data["name"].strip()
    if "term" in data:
        exam.term = data["term"] or None
    if "exam_type" in data:
        exam.exam_type = data["exam_type"] or "other"
    if "max_marks" in data:
        exam.max_marks = int(data["max_marks"] or 100)
    if "start_date" in data:
        exam.start_date = _parse_date(data["start_date"])
    if "end_date" in data:
        exam.end_date = _parse_date(data["end_date"])
    db.session.commit()
    return jsonify(exam.to_dict()), 200


@exam_bp.route("/<int:exam_id>", methods=["DELETE"])
@role_required("admin", "principal")
def delete_exam(exam_id):
    exam = _owned_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    Mark.query.filter_by(organization_id=_org_id(), exam_id=exam.id).delete()
    db.session.delete(exam)
    db.session.commit()
    return jsonify({"success": True}), 200


@exam_bp.route("/<int:exam_id>/publish", methods=["POST"])
@role_required("admin", "principal")
def publish_exam(exam_id):
    exam = _owned_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    exam.status = "published" if (request.get_json(silent=True) or {}).get("published", True) else "draft"
    db.session.commit()
    return jsonify(exam.to_dict()), 200


# ---------------------------------------------------------------------------
# Marks entry
# ---------------------------------------------------------------------------

@exam_bp.route("/<int:exam_id>/marksheet", methods=["GET"])
@token_required
def marksheet(exam_id):
    """Roster + any existing marks for one class+subject (the entry grid)."""
    exam = _owned_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    batch = Batch.query.filter_by(
        id=request.args.get("batch_id", type=int), organization_id=_org_id()
    ).first()
    subject = Subject.query.filter_by(
        id=request.args.get("subject_id", type=int), organization_id=_org_id()
    ).first()
    if not batch or not subject:
        return jsonify({"error": "Class and subject are required"}), 400
    if not _can_access_batch(batch):
        return jsonify({"error": "You cannot enter marks for this class"}), 403

    existing = {
        m.student_id: m
        for m in Mark.query.filter_by(
            organization_id=_org_id(), exam_id=exam.id,
            batch_id=batch.id, subject_id=subject.id,
        ).all()
    }
    rows = []
    for s in _roster(batch):
        m = existing.get(s.id)
        rows.append({
            "student_id": s.id,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "roll_no": s.roll_no,
            "marks_obtained": m.marks_obtained if m else None,
            "is_absent": m.is_absent if m else False,
            "grade": m.grade if m else None,
            "remarks": m.remarks if m else None,
        })
    return jsonify({
        "exam": exam.to_dict(),
        "batch": {"id": batch.id, "label": f"Grade {batch.grade}-{batch.section}"},
        "subject": {"id": subject.id, "name": subject.name},
        "max_marks": exam.max_marks,
        "students": rows,
    }), 200


@exam_bp.route("/<int:exam_id>/marks", methods=["POST"])
@role_required("admin", "principal", "teacher")
def save_marks(exam_id):
    """Bulk upsert marks for a class+subject.

    Body: { batch_id, subject_id, max_marks?, records:[{student_id,
            marks_obtained, is_absent?, remarks?}] }
    """
    exam = _owned_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    data = request.get_json(silent=True) or {}
    batch = Batch.query.filter_by(id=data.get("batch_id"), organization_id=_org_id()).first()
    subject = Subject.query.filter_by(id=data.get("subject_id"), organization_id=_org_id()).first()
    if not batch or not subject:
        return jsonify({"error": "Class and subject are required"}), 400
    if not _can_access_batch(batch):
        return jsonify({"error": "You cannot enter marks for this class"}), 403

    max_marks = int(data.get("max_marks") or exam.max_marks or 100)
    records = data.get("records") or []
    if not isinstance(records, list) or not records:
        return jsonify({"error": "No marks provided"}), 400

    valid_ids = {s.id for s in _roster(batch)}
    entered_by = (getattr(request, "user", {}) or {}).get("user_id")

    saved = 0
    errors = []
    for item in records:
        sid = item.get("student_id")
        if sid not in valid_ids:
            continue
        is_absent = bool(item.get("is_absent"))
        obtained = None
        if not is_absent:
            raw = item.get("marks_obtained")
            if raw is None or raw == "":
                continue  # nothing entered for this student; skip
            try:
                obtained = float(raw)
            except (ValueError, TypeError):
                errors.append(f"Invalid marks for student {sid}")
                continue
            if obtained < 0 or obtained > max_marks:
                errors.append(f"Marks out of range (0-{max_marks}) for student {sid}")
                continue

        pct = None if (is_absent or obtained is None) else round(obtained / max_marks * 100, 1)
        grade = grade_for_percentage(pct)

        m = Mark.query.filter_by(
            organization_id=_org_id(), exam_id=exam.id,
            student_id=sid, subject_id=subject.id,
        ).first()
        if m is None:
            m = Mark(organization_id=_org_id(), exam_id=exam.id,
                     student_id=sid, subject_id=subject.id)
            db.session.add(m)
        m.batch_id = batch.id
        m.max_marks = max_marks
        m.marks_obtained = obtained
        m.is_absent = is_absent
        m.grade = grade
        m.remarks = item.get("remarks")
        m.entered_by = entered_by
        saved += 1

    if errors:
        db.session.rollback()
        return jsonify({"error": "Some marks were invalid", "details": errors}), 400

    db.session.commit()
    return jsonify({"success": True, "saved": saved}), 200


# ---------------------------------------------------------------------------
# Results / report card
# ---------------------------------------------------------------------------

def _build_results(exam, batch):
    """Assemble per-student, per-subject results for a class with ranks."""
    students = _roster(batch)
    student_ids = [s.id for s in students]
    marks = Mark.query.filter(
        Mark.organization_id == exam.organization_id,
        Mark.exam_id == exam.id,
        Mark.student_id.in_(student_ids or [-1]),
    ).all()

    # subject_id -> name (only subjects that actually have marks)
    subj_ids = sorted({m.subject_id for m in marks})
    subjects = {s.id: s.name for s in Subject.query.filter(Subject.id.in_(subj_ids or [-1])).all()}
    by_student = {}
    for m in marks:
        by_student.setdefault(m.student_id, []).append(m)

    rows = []
    for s in students:
        sm = by_student.get(s.id, [])
        subj_rows = []
        total_obtained = 0.0
        total_max = 0
        any_mark = False
        for m in sm:
            any_mark = True
            subj_rows.append({
                "subject_id": m.subject_id,
                "subject": subjects.get(m.subject_id, f"Subject {m.subject_id}"),
                "marks_obtained": m.marks_obtained,
                "max_marks": m.max_marks,
                "is_absent": m.is_absent,
                "grade": m.grade,
            })
            total_max += m.max_marks or 0
            if not m.is_absent and m.marks_obtained is not None:
                total_obtained += m.marks_obtained
        pct = round(total_obtained / total_max * 100, 1) if total_max else None
        rows.append({
            "student_id": s.id,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "roll_no": s.roll_no,
            "subjects": subj_rows,
            "total_obtained": total_obtained if any_mark else None,
            "total_max": total_max if any_mark else None,
            "percentage": pct,
            "overall_grade": grade_for_percentage(pct),
            "has_marks": any_mark,
        })

    # Rank students that have marks, by percentage desc.
    ranked = sorted([r for r in rows if r["has_marks"] and r["percentage"] is not None],
                    key=lambda r: r["percentage"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return {
        "subjects": [{"id": sid, "name": subjects[sid]} for sid in subj_ids],
        "students": rows,
    }


@exam_bp.route("/<int:exam_id>/results", methods=["GET"])
@token_required
def exam_results(exam_id):
    exam = _owned_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    batch = Batch.query.filter_by(
        id=request.args.get("batch_id", type=int), organization_id=_org_id()
    ).first()
    if not batch:
        return jsonify({"error": "Class is required"}), 400
    if not _can_access_batch(batch):
        return jsonify({"error": "You cannot view results for this class"}), 403

    data = _build_results(exam, batch)
    return jsonify({
        "exam": exam.to_dict(),
        "batch": {"id": batch.id, "label": f"Grade {batch.grade}-{batch.section}"},
        **data,
    }), 200


@exam_bp.route("/student/<int:student_id>", methods=["GET"])
@token_required
def student_results(student_id):
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    role = _role()
    if role == "student":
        user_id = (getattr(request, "user", {}) or {}).get("user_id")
        if student.user_id != user_id:
            return jsonify({"error": "You can only view your own results"}), 403
    elif role == "teacher":
        batch = Batch.query.filter_by(
            organization_id=_org_id(), grade=str(student.class_grade), section=student.section
        ).first()
        if not batch or not _can_access_batch(batch):
            return jsonify({"error": "You cannot view this student's results"}), 403
    elif not _is_admin_principal():
        return jsonify({"error": "Not allowed"}), 403

    # Students only see published exams; staff see all.
    exam_q = Exam.query.filter_by(organization_id=_org_id())
    if role == "student":
        exam_q = exam_q.filter_by(status="published")
    exams = {e.id: e for e in exam_q.all()}

    marks = Mark.query.filter(
        Mark.organization_id == _org_id(),
        Mark.student_id == student_id,
        Mark.exam_id.in_(list(exams.keys()) or [-1]),
    ).all()
    subj_ids = sorted({m.subject_id for m in marks})
    subjects = {s.id: s.name for s in Subject.query.filter(Subject.id.in_(subj_ids or [-1])).all()}

    by_exam = {}
    for m in marks:
        by_exam.setdefault(m.exam_id, []).append(m)

    out = []
    for eid, ems in by_exam.items():
        total_obtained = sum((m.marks_obtained or 0) for m in ems if not m.is_absent)
        total_max = sum((m.max_marks or 0) for m in ems)
        pct = round(total_obtained / total_max * 100, 1) if total_max else None
        out.append({
            "exam": exams[eid].to_dict(),
            "subjects": [{
                "subject": subjects.get(m.subject_id, f"Subject {m.subject_id}"),
                "marks_obtained": m.marks_obtained, "max_marks": m.max_marks,
                "is_absent": m.is_absent, "grade": m.grade,
            } for m in ems],
            "total_obtained": total_obtained, "total_max": total_max,
            "percentage": pct, "overall_grade": grade_for_percentage(pct),
        })

    return jsonify({
        "student": {"id": student.id,
                    "name": f"{student.first_name} {student.last_name}".strip(),
                    "class": f"{student.class_grade}-{student.section}"},
        "results": out,
    }), 200
