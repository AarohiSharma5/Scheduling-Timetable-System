"""
Homework / assignments API.

Under /api/assignments (tenant-scoped, role-aware):
  GET    /meta                       Classes + subjects for the compose form
  GET    /                           Assignments visible to the caller
  POST   /                           Create an assignment   (teacher/admin)
  PUT    /<id>                        Edit                    (author/admin)
  DELETE /<id>                        Delete                  (author/admin)
  POST   /<id>/submit                 Student marks submitted (+ optional note)
  GET    /<id>/submissions            Roster + submission status (teacher/admin)
  PUT    /<id>/submissions/<sid>      Grade/feedback          (teacher/admin)
  GET    /student/<id>               Assignments + a student's submission status
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

from models import (
    db, Assignment, AssignmentSubmission, Batch, Subject, Teacher, Student, Guardian,
)
from jwt_utils import token_required, role_required

assignment_bp = Blueprint("assignments", __name__, url_prefix="/api/assignments")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


def _user_id():
    return (getattr(request, "user", {}) or {}).get("user_id")


def _role():
    return (getattr(request, "user", {}) or {}).get("role")


def _is_admin_principal():
    # Coordinators share the school-wide academic oversight of a principal.
    return _role() in ("admin", "principal", "coordinator")


def _acting_teacher():
    if _role() != "teacher":
        return None
    return Teacher.query.filter_by(user_id=_user_id(), organization_id=_org_id()).first()


def _teacher_batch_ids(teacher):
    ids = set(teacher.assigned_batch_ids or [])
    if teacher.class_teacher_batch_id:
        ids.add(teacher.class_teacher_batch_id)
    return ids


def _student_batch(student):
    if not student:
        return None
    return Batch.query.filter_by(
        organization_id=student.organization_id,
        grade=str(student.class_grade), section=student.section,
    ).first()


def _can_access_batch(batch):
    if batch is None or batch.organization_id != _org_id():
        return False
    if _is_admin_principal():
        return True
    teacher = _acting_teacher()
    return bool(teacher) and batch.id in _teacher_batch_ids(teacher)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _decorate(assignments, *, extra_by_id=None):
    subj = {s.id: s.name for s in Subject.query.filter_by(organization_id=_org_id()).all()}
    batches = {b.id: f"Grade {b.grade}-{b.section}"
               for b in Batch.query.filter_by(organization_id=_org_id()).all()}
    from models import User
    authors = {u.id: u.name for u in User.query.filter_by(organization_id=_org_id()).all()}
    out = []
    for a in assignments:
        out.append(a.to_dict(
            subject_name=subj.get(a.subject_id),
            batch_label=batches.get(a.batch_id),
            author_name=authors.get(a.created_by),
            extra=(extra_by_id or {}).get(a.id),
        ))
    return out


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

@assignment_bp.route("/meta", methods=["GET"])
@role_required("admin", "principal", "coordinator", "teacher")
def meta():
    batches = Batch.query.filter_by(organization_id=_org_id()).all()
    if not _is_admin_principal():
        teacher = _acting_teacher()
        allowed = _teacher_batch_ids(teacher) if teacher else set()
        batches = [b for b in batches if b.id in allowed]
    batches.sort(key=lambda b: (str(b.grade), b.section))
    subjects = Subject.query.filter_by(organization_id=_org_id()).order_by(Subject.name).all()
    return jsonify({
        "classes": [{"batch_id": b.id, "label": f"Grade {b.grade}-{b.section}",
                     "subject_ids": b.subject_ids or []} for b in batches],
        "subjects": [{"id": s.id, "name": s.name} for s in subjects],
    }), 200


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@assignment_bp.route("", methods=["GET"])
@token_required
def list_assignments():
    role = _role()
    q = Assignment.query.filter_by(organization_id=_org_id())

    if _is_admin_principal():
        assignments = q.order_by(Assignment.created_at.desc()).all()
        return jsonify(_decorate(assignments)), 200

    if role == "teacher":
        teacher = _acting_teacher()
        allowed = _teacher_batch_ids(teacher) if teacher else set()
        assignments = [a for a in q.order_by(Assignment.created_at.desc()).all()
                       if a.batch_id in allowed]
        return jsonify(_decorate(assignments)), 200

    if role == "student":
        student = Student.query.filter_by(organization_id=_org_id(), user_id=_user_id()).first()
        batch = _student_batch(student)
        if not batch:
            return jsonify([]), 200
        assignments = q.filter_by(batch_id=batch.id).order_by(Assignment.due_date.desc().nullslast()).all()
        subs = {s.assignment_id: s for s in AssignmentSubmission.query.filter_by(
            organization_id=_org_id(), student_id=student.id).all()}
        extra = {a.id: {"my_status": (subs[a.id].status if a.id in subs else "pending"),
                        "my_grade": (subs[a.id].grade if a.id in subs else None)}
                 for a in assignments}
        return jsonify(_decorate(assignments, extra_by_id=extra)), 200

    return jsonify({"error": "Not allowed"}), 403


# ---------------------------------------------------------------------------
# Create / edit / delete
# ---------------------------------------------------------------------------

@assignment_bp.route("", methods=["POST"])
@role_required("admin", "principal", "coordinator", "teacher")
def create_assignment():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400
    batch = Batch.query.filter_by(id=data.get("batch_id"), organization_id=_org_id()).first()
    if not batch:
        return jsonify({"error": "Class is required"}), 400
    if not _can_access_batch(batch):
        return jsonify({"error": "You can only set homework for your own classes"}), 403

    subject_id = data.get("subject_id") or None
    if subject_id and not Subject.query.filter_by(id=subject_id, organization_id=_org_id()).first():
        return jsonify({"error": "Subject not found"}), 400

    a = Assignment(
        organization_id=_org_id(), batch_id=batch.id, subject_id=subject_id,
        title=title, description=(data.get("description") or None),
        due_date=_parse_date(data.get("due_date")), created_by=_user_id(),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(_decorate([a])[0]), 201


def _owned(aid):
    return Assignment.query.filter_by(id=aid, organization_id=_org_id()).first()


def _can_modify(a):
    return _is_admin_principal() or a.created_by == _user_id()


@assignment_bp.route("/<int:aid>", methods=["PUT"])
@role_required("admin", "principal", "coordinator", "teacher")
def update_assignment(aid):
    a = _owned(aid)
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    if not _can_modify(a):
        return jsonify({"error": "You cannot edit this assignment"}), 403
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        a.title = data["title"].strip()
    if "description" in data:
        a.description = data["description"] or None
    if "due_date" in data:
        a.due_date = _parse_date(data["due_date"])
    if "subject_id" in data:
        a.subject_id = data["subject_id"] or None
    db.session.commit()
    return jsonify(_decorate([a])[0]), 200


@assignment_bp.route("/<int:aid>", methods=["DELETE"])
@role_required("admin", "principal", "coordinator", "teacher")
def delete_assignment(aid):
    a = _owned(aid)
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    if not _can_modify(a):
        return jsonify({"error": "You cannot delete this assignment"}), 403
    AssignmentSubmission.query.filter_by(organization_id=_org_id(), assignment_id=a.id).delete()
    db.session.delete(a)
    db.session.commit()
    return jsonify({"success": True}), 200


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

@assignment_bp.route("/<int:aid>/submit", methods=["POST"])
@role_required("student")
def submit_assignment(aid):
    a = _owned(aid)
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    student = Student.query.filter_by(organization_id=_org_id(), user_id=_user_id()).first()
    batch = _student_batch(student)
    if not student or not batch or batch.id != a.batch_id:
        return jsonify({"error": "This assignment isn't for your class"}), 403

    data = request.get_json(silent=True) or {}
    sub = AssignmentSubmission.query.filter_by(
        organization_id=_org_id(), assignment_id=a.id, student_id=student.id).first()
    if not sub:
        sub = AssignmentSubmission(organization_id=_org_id(), assignment_id=a.id,
                                   student_id=student.id)
        db.session.add(sub)
    sub.status = "submitted"
    sub.note = data.get("note") or None
    sub.submitted_at = datetime.utcnow()
    db.session.commit()
    return jsonify(sub.to_dict()), 200


@assignment_bp.route("/<int:aid>/submissions", methods=["GET"])
@role_required("admin", "principal", "coordinator", "teacher")
def list_submissions(aid):
    a = _owned(aid)
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    batch = Batch.query.get(a.batch_id)
    if not _can_access_batch(batch):
        return jsonify({"error": "Not allowed"}), 403

    students = Student.query.filter(
        Student.organization_id == _org_id(),
        Student.class_grade == str(batch.grade),
        Student.section == batch.section,
        Student.status == "Active",
    ).all()
    students.sort(key=lambda s: (s.roll_no if s.roll_no is not None else 9999,
                                 (s.first_name or "").lower()))
    subs = {s.student_id: s for s in AssignmentSubmission.query.filter_by(
        organization_id=_org_id(), assignment_id=a.id).all()}
    rows = []
    for s in students:
        sub = subs.get(s.id)
        rows.append({
            "student_id": s.id, "name": f"{s.first_name} {s.last_name}".strip(),
            "roll_no": s.roll_no,
            "status": sub.status if sub else "pending",
            "note": sub.note if sub else None,
            "grade": sub.grade if sub else None,
            "feedback": sub.feedback if sub else None,
            "submitted_at": sub.submitted_at.isoformat() if (sub and sub.submitted_at) else None,
        })
    return jsonify({
        "assignment": _decorate([a])[0],
        "students": rows,
    }), 200


@assignment_bp.route("/<int:aid>/submissions/<int:student_id>", methods=["PUT"])
@role_required("admin", "principal", "coordinator", "teacher")
def grade_submission(aid, student_id):
    a = _owned(aid)
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    batch = Batch.query.get(a.batch_id)
    if not _can_access_batch(batch):
        return jsonify({"error": "Not allowed"}), 403
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json(silent=True) or {}
    sub = AssignmentSubmission.query.filter_by(
        organization_id=_org_id(), assignment_id=a.id, student_id=student_id).first()
    if not sub:
        sub = AssignmentSubmission(organization_id=_org_id(), assignment_id=a.id,
                                   student_id=student_id, status="submitted")
        db.session.add(sub)
    if "grade" in data:
        sub.grade = data["grade"] or None
    if "feedback" in data:
        sub.feedback = data["feedback"] or None
    sub.status = "graded"
    db.session.commit()
    return jsonify(sub.to_dict()), 200


# ---------------------------------------------------------------------------
# Per-student view (student self / parent child / staff)
# ---------------------------------------------------------------------------

@assignment_bp.route("/student/<int:student_id>", methods=["GET"])
@token_required
def student_assignments(student_id):
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    role = _role()
    if role == "student":
        if student.user_id != _user_id():
            return jsonify({"error": "You can only view your own homework"}), 403
    elif role == "parent":
        if not Guardian.query.filter_by(
            organization_id=_org_id(), user_id=_user_id(), student_id=student.id).first():
            return jsonify({"error": "You can only view your own children's homework"}), 403
    elif role == "teacher":
        if not _can_access_batch(_student_batch(student)):
            return jsonify({"error": "Not allowed"}), 403
    elif not _is_admin_principal():
        return jsonify({"error": "Not allowed"}), 403

    batch = _student_batch(student)
    if not batch:
        return jsonify({"student": {"id": student.id}, "assignments": []}), 200
    assignments = Assignment.query.filter_by(
        organization_id=_org_id(), batch_id=batch.id
    ).order_by(Assignment.due_date.desc().nullslast()).all()
    subs = {s.assignment_id: s for s in AssignmentSubmission.query.filter_by(
        organization_id=_org_id(), student_id=student.id).all()}
    extra = {a.id: {"my_status": (subs[a.id].status if a.id in subs else "pending"),
                    "my_grade": (subs[a.id].grade if a.id in subs else None),
                    "my_feedback": (subs[a.id].feedback if a.id in subs else None)}
             for a in assignments}
    return jsonify({
        "student": {"id": student.id,
                    "name": f"{student.first_name} {student.last_name}".strip(),
                    "class": f"{student.class_grade}-{student.section}"},
        "assignments": _decorate(assignments, extra_by_id=extra),
    }), 200
