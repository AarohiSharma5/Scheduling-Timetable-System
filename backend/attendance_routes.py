"""
Attendance API — daily and period-wise student attendance.

Endpoints (all under /api/attendance, all tenant-scoped):
  GET  /classes                 Classes the caller may mark/view
  GET  /roster                  Students of a class + any existing marks for a date/period
  POST /mark                    Bulk upsert attendance for a class
  GET  /summary                 Per-student attendance % over a date range
  GET  /student/<id>            One student's attendance history
  GET  /today                   Org-wide attendance snapshot for a date (dashboard)

Roles:
  - admin/principal: every class, read + write
  - teacher: only their assigned/class-teacher classes
  - student: only their own history (via /student/<id>)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date as date_cls
from sqlalchemy import func

from models import db, AttendanceRecord, Student, Batch, Teacher, Subject, User, Guardian
from jwt_utils import token_required, role_required

attendance_bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")

VALID_STATUSES = {"present", "absent", "late", "excused"}


# ---------------------------------------------------------------------------
# Helpers (kept local to avoid a circular import with routes.py)
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


def _parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default


def _allowed_batch_ids(teacher):
    """Set of batch ids a teacher may touch (taught + class-teacher of)."""
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
    """Active students of a class, matched by grade + section, sorted by roll."""
    students = Student.query.filter(
        Student.organization_id == _org_id(),
        Student.class_grade == str(batch.grade),
        Student.section == batch.section,
        Student.status == "Active",
    ).all()
    students.sort(key=lambda s: (s.roll_no if s.roll_no is not None else 9999,
                                 (s.first_name or "").lower()))
    return students


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@attendance_bp.route("/classes", methods=["GET"])
@token_required
def attendance_classes():
    """Classes the caller may take attendance for."""
    org_id = _org_id()
    batches = Batch.query.filter_by(organization_id=org_id).all()

    if not _is_admin_principal():
        teacher = _acting_teacher()
        if not teacher:
            return jsonify({"error": "Only teachers and admins can take attendance"}), 403
        allowed = _allowed_batch_ids(teacher)
        batches = [b for b in batches if b.id in allowed]

    batches.sort(key=lambda b: (str(b.grade), b.section))
    out = []
    for b in batches:
        out.append({
            "batch_id": b.id,
            "grade": b.grade,
            "section": b.section,
            "label": f"Grade {b.grade}-{b.section}",
            "student_count": len(_roster(b)),
        })
    return jsonify(out), 200


@attendance_bp.route("/roster", methods=["GET"])
@token_required
def attendance_roster():
    """Roster for a class with any existing marks for the given date/period."""
    batch = Batch.query.filter_by(
        id=request.args.get("batch_id", type=int), organization_id=_org_id()
    ).first()
    if not batch:
        return jsonify({"error": "Class not found"}), 404
    if not _can_access_batch(batch):
        return jsonify({"error": "You cannot take attendance for this class"}), 403

    on_date = _parse_date(request.args.get("date"), default=date_cls.today())
    period_number = request.args.get("period_number", default=0, type=int)

    students = _roster(batch)
    existing = {
        r.student_id: r
        for r in AttendanceRecord.query.filter_by(
            organization_id=_org_id(), batch_id=batch.id,
            date=on_date, period_number=period_number,
        ).all()
    }

    rows = []
    for s in students:
        rec = existing.get(s.id)
        rows.append({
            "student_id": s.id,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "roll_no": s.roll_no,
            "admission_no": s.admission_no,
            # default to "present" so a teacher only flips the absentees
            "status": rec.status if rec else "present",
            "remarks": rec.remarks if rec else None,
            "marked": rec is not None,
        })
    return jsonify({
        "batch": {"id": batch.id, "label": f"Grade {batch.grade}-{batch.section}"},
        "date": on_date.isoformat(),
        "period_number": period_number,
        "students": rows,
        "already_marked": bool(existing),
    }), 200


@attendance_bp.route("/mark", methods=["POST"])
@role_required("admin", "principal", "teacher")
def attendance_mark():
    """Bulk upsert attendance for a class on a date/period.

    Body: { batch_id, date, period_number (0=daily), subject_id?,
            records: [{ student_id, status, remarks? }] }
    """
    org_id = _org_id()
    data = request.get_json(silent=True) or {}

    batch = Batch.query.filter_by(id=data.get("batch_id"), organization_id=org_id).first()
    if not batch:
        return jsonify({"error": "Class not found"}), 404
    if not _can_access_batch(batch):
        return jsonify({"error": "You cannot take attendance for this class"}), 403

    on_date = _parse_date(data.get("date"), default=date_cls.today())
    if on_date > date_cls.today():
        return jsonify({"error": "Cannot mark attendance for a future date"}), 400
    period_number = int(data.get("period_number") or 0)
    subject_id = data.get("subject_id")
    records = data.get("records") or []
    if not isinstance(records, list) or not records:
        return jsonify({"error": "No attendance records provided"}), 400

    # Only students that actually belong to this class may be marked.
    valid_student_ids = {s.id for s in _roster(batch)}
    marked_by = (getattr(request, "user", {}) or {}).get("user_id")

    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    saved = 0
    for item in records:
        sid = item.get("student_id")
        status = (item.get("status") or "present").lower()
        if sid not in valid_student_ids or status not in VALID_STATUSES:
            continue
        rec = AttendanceRecord.query.filter_by(
            organization_id=org_id, student_id=sid,
            date=on_date, period_number=period_number,
        ).first()
        if rec is None:
            rec = AttendanceRecord(
                organization_id=org_id, student_id=sid, batch_id=batch.id,
                date=on_date, period_number=period_number,
            )
            db.session.add(rec)
        rec.batch_id = batch.id
        rec.subject_id = subject_id
        rec.status = status
        rec.remarks = item.get("remarks")
        rec.marked_by = marked_by
        counts[status] += 1
        saved += 1

    db.session.commit()
    return jsonify({
        "success": True,
        "saved": saved,
        "date": on_date.isoformat(),
        "period_number": period_number,
        "summary": counts,
    }), 200


@attendance_bp.route("/summary", methods=["GET"])
@token_required
def attendance_summary():
    """Per-student attendance totals/percentage for a class over a date range."""
    batch = Batch.query.filter_by(
        id=request.args.get("batch_id", type=int), organization_id=_org_id()
    ).first()
    if not batch:
        return jsonify({"error": "Class not found"}), 404
    if not _can_access_batch(batch):
        return jsonify({"error": "You cannot view attendance for this class"}), 403

    today = date_cls.today()
    start = _parse_date(request.args.get("from"), default=today.replace(day=1))
    end = _parse_date(request.args.get("to"), default=today)
    period_number = request.args.get("period_number", default=0, type=int)

    students = _roster(batch)
    student_ids = [s.id for s in students]

    # Aggregate counts per (student, status) in one grouped query.
    agg = {}
    if student_ids:
        rows = (
            db.session.query(
                AttendanceRecord.student_id,
                AttendanceRecord.status,
                func.count(AttendanceRecord.id),
            )
            .filter(
                AttendanceRecord.organization_id == _org_id(),
                AttendanceRecord.student_id.in_(student_ids),
                AttendanceRecord.period_number == period_number,
                AttendanceRecord.date >= start,
                AttendanceRecord.date <= end,
            )
            .group_by(AttendanceRecord.student_id, AttendanceRecord.status)
            .all()
        )
        for sid, status, n in rows:
            agg.setdefault(sid, {}).update({status: n})

    out = []
    for s in students:
        c = agg.get(s.id, {})
        present = c.get("present", 0)
        absent = c.get("absent", 0)
        late = c.get("late", 0)
        excused = c.get("excused", 0)
        total = present + absent + late + excused
        # late still counts as attended for the percentage.
        attended = present + late
        pct = round(attended / total * 100, 1) if total else None
        out.append({
            "student_id": s.id,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "roll_no": s.roll_no,
            "present": present, "absent": absent, "late": late,
            "excused": excused, "total": total, "percentage": pct,
        })
    return jsonify({
        "batch": {"id": batch.id, "label": f"Grade {batch.grade}-{batch.section}"},
        "from": start.isoformat(), "to": end.isoformat(),
        "period_number": period_number,
        "students": out,
    }), 200


@attendance_bp.route("/student/<int:student_id>", methods=["GET"])
@token_required
def attendance_student(student_id):
    """One student's attendance history (own record for students)."""
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    role = _role()
    if role == "student":
        # Students may only see their own attendance.
        user_id = (getattr(request, "user", {}) or {}).get("user_id")
        if student.user_id != user_id:
            return jsonify({"error": "You can only view your own attendance"}), 403
    elif role == "teacher":
        batch = Batch.query.filter_by(
            organization_id=_org_id(), grade=str(student.class_grade),
            section=student.section,
        ).first()
        if not batch or not _can_access_batch(batch):
            return jsonify({"error": "You cannot view this student's attendance"}), 403
    elif role == "parent":
        link = Guardian.query.filter_by(
            organization_id=_org_id(), user_id=(getattr(request, "user", {}) or {}).get("user_id"),
            student_id=student_id,
        ).first()
        if not link:
            return jsonify({"error": "You can only view your own children's attendance"}), 403
    elif not _is_admin_principal():
        return jsonify({"error": "Not allowed"}), 403

    today = date_cls.today()
    start = _parse_date(request.args.get("from"), default=today.replace(month=1, day=1))
    end = _parse_date(request.args.get("to"), default=today)
    period_number = request.args.get("period_number", default=0, type=int)

    records = (
        AttendanceRecord.query.filter(
            AttendanceRecord.organization_id == _org_id(),
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.period_number == period_number,
            AttendanceRecord.date >= start,
            AttendanceRecord.date <= end,
        )
        .order_by(AttendanceRecord.date.desc())
        .all()
    )
    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for r in records:
        if r.status in counts:
            counts[r.status] += 1
    total = sum(counts.values())
    attended = counts["present"] + counts["late"]
    return jsonify({
        "student": {"id": student.id,
                    "name": f"{student.first_name} {student.last_name}".strip(),
                    "class": f"{student.class_grade}-{student.section}"},
        "from": start.isoformat(), "to": end.isoformat(),
        "summary": {**counts, "total": total,
                    "percentage": round(attended / total * 100, 1) if total else None},
        "records": [r.to_dict() for r in records],
    }), 200


@attendance_bp.route("/today", methods=["GET"])
@role_required("admin", "principal", "teacher")
def attendance_today():
    """Org-wide daily attendance snapshot for a date (default today)."""
    org_id = _org_id()
    on_date = _parse_date(request.args.get("date"), default=date_cls.today())

    rows = (
        db.session.query(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.organization_id == org_id,
            AttendanceRecord.date == on_date,
            AttendanceRecord.period_number == 0,
        )
        .group_by(AttendanceRecord.status)
        .all()
    )
    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for status, n in rows:
        if status in counts:
            counts[status] = n
    total = sum(counts.values())
    attended = counts["present"] + counts["late"]

    # How many classes have been marked today (distinct batches with a daily mark).
    classes_marked = (
        db.session.query(func.count(func.distinct(AttendanceRecord.batch_id)))
        .filter(
            AttendanceRecord.organization_id == org_id,
            AttendanceRecord.date == on_date,
            AttendanceRecord.period_number == 0,
        )
        .scalar()
    ) or 0
    total_classes = Batch.query.filter_by(organization_id=org_id).count()

    return jsonify({
        "date": on_date.isoformat(),
        "counts": counts,
        "total_marked": total,
        "present_percentage": round(attended / total * 100, 1) if total else None,
        "classes_marked": classes_marked,
        "total_classes": total_classes,
    }), 200
