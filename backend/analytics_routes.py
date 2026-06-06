"""
Analytics API (/api/analytics) - admin/principal only.

  GET /overview   Org-scoped KPIs across students, attendance, fees, exams,
                  library, transport and inventory.
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import func

from models import (
    db, Student, Teacher, AttendanceRecord, FeeInvoice, Payment, Exam, Mark,
    Book, BookLoan, TransportRoute, TransportAssignment, InventoryItem,
)
from jwt_utils import role_required

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


@analytics_bp.route("/overview", methods=["GET"])
@role_required("admin", "principal", "coordinator")
def overview():
    oid = _org_id()

    # --- students ---
    students = Student.query.filter_by(organization_id=oid, status="Active").all()
    by_grade = {}
    for s in students:
        by_grade[str(s.class_grade)] = by_grade.get(str(s.class_grade), 0) + 1
    teacher_count = Teacher.query.filter_by(organization_id=oid).count()

    # --- attendance (overall present rate across all marks) ---
    att_rows = db.session.query(
        AttendanceRecord.status, func.count(AttendanceRecord.id)
    ).filter(AttendanceRecord.organization_id == oid).group_by(AttendanceRecord.status).all()
    att = {status: count for status, count in att_rows}
    att_total = sum(att.values())
    present_like = att.get("present", 0) + att.get("late", 0)
    attendance_rate = round(present_like / att_total * 100, 1) if att_total else None

    # --- fees ---
    invoices = FeeInvoice.query.filter_by(organization_id=oid).all()
    billed = round(sum(i.amount for i in invoices), 2)
    collected = round(
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.organization_id == oid).scalar() or 0, 2)

    # --- exams (pass rate on published exams; pass = >= 33%) ---
    published_ids = [e.id for e in Exam.query.filter_by(organization_id=oid, status="published").all()]
    marks = Mark.query.filter(
        Mark.organization_id == oid, Mark.exam_id.in_(published_ids or [-1]),
        Mark.marks_obtained.isnot(None)).all()
    graded = len(marks)
    passed = sum(1 for m in marks if m.max_marks and (m.marks_obtained / m.max_marks) >= 0.33)
    pass_rate = round(passed / graded * 100, 1) if graded else None

    # --- library ---
    book_count = Book.query.filter_by(organization_id=oid).count()
    issued = BookLoan.query.filter_by(organization_id=oid, status="issued").all()
    overdue = sum(1 for l in issued if l.is_overdue())

    # --- transport ---
    route_count = TransportRoute.query.filter_by(organization_id=oid).count()
    transported = TransportAssignment.query.filter_by(organization_id=oid).count()

    # --- inventory ---
    inv_items = InventoryItem.query.filter_by(organization_id=oid).all()
    low_stock = sum(1 for i in inv_items if i.quantity <= (i.min_quantity or 0))

    return jsonify({
        "students": {
            "total": len(students),
            "teachers": teacher_count,
            "by_grade": dict(sorted(by_grade.items())),
        },
        "attendance": {
            "rate": attendance_rate,
            "present": att.get("present", 0), "absent": att.get("absent", 0),
            "late": att.get("late", 0), "marks": att_total,
        },
        "fees": {
            "billed": billed, "collected": collected,
            "outstanding": round(billed - collected, 2),
            "collection_rate": round(collected / billed * 100, 1) if billed else None,
        },
        "exams": {"published": len(published_ids), "graded_marks": graded, "pass_rate": pass_rate},
        "library": {"books": book_count, "issued": len(issued), "overdue": overdue},
        "transport": {"routes": route_count, "students": transported},
        "inventory": {"items": len(inv_items), "low_stock": low_stock},
    }), 200
