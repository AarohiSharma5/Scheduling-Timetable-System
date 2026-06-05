"""
Fees / payments API.

Admin/principal (under /api/fees):
  GET    /structures               List fee structures
  POST   /structures               Create a fee structure
  DELETE /structures/<id>          Delete a structure (and its invoices)
  POST   /structures/<id>/generate Issue invoices to matching students
  GET    /invoices                 List invoices (filter by status/grade/student)
  POST   /invoices                 Create an ad-hoc invoice for a student
  GET    /invoices/<id>            Invoice detail + payments
  POST   /invoices/<id>/payments   Record a payment
  GET    /summary                  Billed / collected / outstanding totals

Parent/student self-service:
  GET    /student/<id>             Invoices + payments for a student
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

from models import (
    db, FeeStructure, FeeInvoice, Payment, Student, Guardian,
    recompute_invoice_status,
)
from jwt_utils import token_required, role_required

fees_bp = Blueprint("fees", __name__, url_prefix="/api/fees")


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
    return _role() in ("admin", "principal")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _student_name(s):
    return f"{s.first_name} {s.last_name}".strip()


def _can_view_student(student):
    """Admins/principals: any. Parents: their children. Students: themselves."""
    if student is None or student.organization_id != _org_id():
        return False
    if _is_admin_principal():
        return True
    role = _role()
    if role == "parent":
        return Guardian.query.filter_by(
            organization_id=_org_id(), user_id=_user_id(), student_id=student.id
        ).first() is not None
    if role == "student":
        return student.user_id == _user_id()
    return False


# ---------------------------------------------------------------------------
# Fee structures
# ---------------------------------------------------------------------------

@fees_bp.route("/structures", methods=["GET"])
@role_required("admin", "principal")
def list_structures():
    items = FeeStructure.query.filter_by(organization_id=_org_id()).order_by(
        FeeStructure.created_at.desc()
    ).all()
    return jsonify([s.to_dict() for s in items]), 200


@fees_bp.route("/structures", methods=["POST"])
@role_required("admin", "principal")
def create_structure():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Fee name is required"}), 400
    try:
        amount = float(data.get("amount") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    grade = data.get("grade")
    grade = None if (grade in (None, "", "all")) else str(grade)
    s = FeeStructure(
        organization_id=_org_id(), name=name, amount=amount, grade=grade,
        term=(data.get("term") or None), due_date=_parse_date(data.get("due_date")),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@fees_bp.route("/structures/<int:structure_id>", methods=["DELETE"])
@role_required("admin", "principal")
def delete_structure(structure_id):
    s = FeeStructure.query.filter_by(id=structure_id, organization_id=_org_id()).first()
    if not s:
        return jsonify({"error": "Fee structure not found"}), 404
    invoice_ids = [i.id for i in FeeInvoice.query.filter_by(
        organization_id=_org_id(), fee_structure_id=s.id).all()]
    if invoice_ids:
        Payment.query.filter(Payment.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        FeeInvoice.query.filter(FeeInvoice.id.in_(invoice_ids)).delete(synchronize_session=False)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"success": True}), 200


@fees_bp.route("/structures/<int:structure_id>/generate", methods=["POST"])
@role_required("admin", "principal")
def generate_invoices(structure_id):
    """Issue an invoice of this structure to every matching active student."""
    s = FeeStructure.query.filter_by(id=structure_id, organization_id=_org_id()).first()
    if not s:
        return jsonify({"error": "Fee structure not found"}), 404

    q = Student.query.filter_by(organization_id=_org_id(), status="Active")
    if s.grade:
        q = q.filter(Student.class_grade == s.grade)
    students = q.all()

    existing = {
        i.student_id for i in FeeInvoice.query.filter_by(
            organization_id=_org_id(), fee_structure_id=s.id).all()
    }
    created = 0
    for stu in students:
        if stu.id in existing:
            continue
        db.session.add(FeeInvoice(
            organization_id=_org_id(), student_id=stu.id, fee_structure_id=s.id,
            title=s.name, amount=s.amount, due_date=s.due_date, status="pending",
        ))
        created += 1
    db.session.commit()
    return jsonify({"success": True, "created": created, "skipped": len(students) - created}), 200


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@fees_bp.route("/invoices", methods=["GET"])
@role_required("admin", "principal")
def list_invoices():
    q = FeeInvoice.query.filter_by(organization_id=_org_id())
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    student_id = request.args.get("student_id", type=int)
    if student_id:
        q = q.filter_by(student_id=student_id)
    invoices = q.order_by(FeeInvoice.created_at.desc()).all()

    grade = request.args.get("grade")
    sids = {i.student_id for i in invoices}
    students = {s.id: s for s in Student.query.filter(Student.id.in_(sids or [-1])).all()}
    out = []
    for inv in invoices:
        stu = students.get(inv.student_id)
        if grade and (not stu or str(stu.class_grade) != str(grade)):
            continue
        out.append(inv.to_dict(student_name=_student_name(stu) if stu else None))
    return jsonify(out), 200


@fees_bp.route("/invoices", methods=["POST"])
@role_required("admin", "principal")
def create_invoice():
    data = request.get_json(silent=True) or {}
    student = Student.query.filter_by(id=data.get("student_id"), organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 400
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400
    try:
        amount = float(data.get("amount") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    inv = FeeInvoice(
        organization_id=_org_id(), student_id=student.id, title=title,
        amount=amount, due_date=_parse_date(data.get("due_date")), status="pending",
    )
    db.session.add(inv)
    db.session.commit()
    return jsonify(inv.to_dict(student_name=_student_name(student))), 201


@fees_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@token_required
def invoice_detail(invoice_id):
    inv = FeeInvoice.query.filter_by(id=invoice_id, organization_id=_org_id()).first()
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
    student = Student.query.get(inv.student_id)
    if not _can_view_student(student):
        return jsonify({"error": "Not allowed"}), 403
    return jsonify({
        **inv.to_dict(student_name=_student_name(student) if student else None),
        "payments": [p.to_dict() for p in sorted(inv.payments, key=lambda p: p.id)],
    }), 200


@fees_bp.route("/invoices/<int:invoice_id>/payments", methods=["POST"])
@role_required("admin", "principal")
def record_payment(invoice_id):
    inv = FeeInvoice.query.filter_by(id=invoice_id, organization_id=_org_id()).first()
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400
    if amount <= 0:
        return jsonify({"error": "Payment amount must be greater than zero"}), 400
    if amount > inv.amount - inv.amount_paid() + 0.001:
        return jsonify({"error": "Payment exceeds the outstanding balance"}), 400

    payment = Payment(
        organization_id=_org_id(), invoice_id=inv.id, student_id=inv.student_id,
        amount=round(amount, 2), method=(data.get("method") or "cash"),
        reference=(data.get("reference") or None),
        paid_on=_parse_date(data.get("paid_on")) or datetime.utcnow().date(),
        recorded_by=_user_id(),
    )
    db.session.add(payment)
    db.session.flush()
    recompute_invoice_status(inv)
    db.session.commit()
    return jsonify({
        "success": True, "payment": payment.to_dict(),
        "invoice": inv.to_dict(),
    }), 201


# ---------------------------------------------------------------------------
# Summary + student view
# ---------------------------------------------------------------------------

@fees_bp.route("/summary", methods=["GET"])
@role_required("admin", "principal")
def fees_summary():
    invoices = FeeInvoice.query.filter_by(organization_id=_org_id()).all()
    billed = round(sum(i.amount for i in invoices), 2)
    collected = round(sum(i.amount_paid() for i in invoices), 2)
    by_status = {"pending": 0, "partial": 0, "paid": 0, "waived": 0}
    for i in invoices:
        by_status[i.status] = by_status.get(i.status, 0) + 1
    return jsonify({
        "billed": billed, "collected": collected,
        "outstanding": round(billed - collected, 2),
        "invoice_count": len(invoices), "by_status": by_status,
    }), 200


@fees_bp.route("/my", methods=["GET"])
@role_required("student")
def my_invoices():
    student = Student.query.filter_by(organization_id=_org_id(), user_id=_user_id()).first()
    if not student:
        return jsonify({"error": "No student record is linked to your account"}), 404
    return student_invoices(student.id)


@fees_bp.route("/student/<int:student_id>", methods=["GET"])
@token_required
def student_invoices(student_id):
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    if not _can_view_student(student):
        return jsonify({"error": "Not allowed"}), 403

    invoices = FeeInvoice.query.filter_by(
        organization_id=_org_id(), student_id=student_id
    ).order_by(FeeInvoice.created_at.desc()).all()
    billed = round(sum(i.amount for i in invoices), 2)
    paid = round(sum(i.amount_paid() for i in invoices), 2)
    return jsonify({
        "student": {"id": student.id, "name": _student_name(student),
                    "class": f"{student.class_grade}-{student.section}"},
        "totals": {"billed": billed, "paid": paid, "outstanding": round(billed - paid, 2)},
        "invoices": [{
            **inv.to_dict(),
            "payments": [p.to_dict() for p in sorted(inv.payments, key=lambda p: p.id)],
        } for inv in invoices],
    }), 200
