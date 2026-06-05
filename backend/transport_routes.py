"""
Transport API (/api/transport).

Staff (admin/principal):
  GET    /routes                  List routes (with assigned counts)
  POST   /routes                  Create a route
  PUT    /routes/<id>             Edit a route
  DELETE /routes/<id>             Delete a route (and its assignments)
  GET    /routes/<id>/students    Students on a route
  POST   /routes/<id>/students    Assign a student (body: student_id, stop_name)
  DELETE /assignments/<id>        Unassign a student

Self-service:
  GET    /student/<id>            A student's transport (student self / parent / staff)
"""

from flask import Blueprint, request, jsonify

from models import db, TransportRoute, TransportAssignment, Student, Guardian
from jwt_utils import token_required, role_required

transport_bp = Blueprint("transport", __name__, url_prefix="/api/transport")

_STAFF = ("admin", "principal")


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


def _role():
    return (getattr(request, "user", {}) or {}).get("role")


def _user_id():
    return (getattr(request, "user", {}) or {}).get("user_id")


def _student_name(s):
    return f"{s.first_name} {s.last_name}".strip() if s else None


@transport_bp.route("/routes", methods=["GET"])
@role_required(*_STAFF)
def list_routes():
    routes = TransportRoute.query.filter_by(organization_id=_org_id()).order_by(TransportRoute.name).all()
    counts = {}
    for a in TransportAssignment.query.filter_by(organization_id=_org_id()).all():
        counts[a.route_id] = counts.get(a.route_id, 0) + 1
    return jsonify([r.to_dict(assigned_count=counts.get(r.id, 0)) for r in routes]), 200


@transport_bp.route("/routes", methods=["POST"])
@role_required(*_STAFF)
def create_route():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Route name is required"}), 400
    cap = data.get("capacity")
    try:
        cap = int(cap) if cap not in (None, "") else None
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid capacity"}), 400
    r = TransportRoute(
        organization_id=_org_id(), name=name, description=(data.get("description") or None),
        driver_name=(data.get("driver_name") or None), driver_phone=(data.get("driver_phone") or None),
        vehicle_no=(data.get("vehicle_no") or None), capacity=cap,
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict(assigned_count=0)), 201


@transport_bp.route("/routes/<int:route_id>", methods=["PUT"])
@role_required(*_STAFF)
def update_route(route_id):
    r = TransportRoute.query.filter_by(id=route_id, organization_id=_org_id()).first()
    if not r:
        return jsonify({"error": "Route not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        r.name = data["name"].strip()
    for field in ("description", "driver_name", "driver_phone", "vehicle_no"):
        if field in data:
            setattr(r, field, data[field] or None)
    if "capacity" in data:
        try:
            r.capacity = int(data["capacity"]) if data["capacity"] not in (None, "") else None
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid capacity"}), 400
    db.session.commit()
    return jsonify(r.to_dict()), 200


@transport_bp.route("/routes/<int:route_id>", methods=["DELETE"])
@role_required(*_STAFF)
def delete_route(route_id):
    r = TransportRoute.query.filter_by(id=route_id, organization_id=_org_id()).first()
    if not r:
        return jsonify({"error": "Route not found"}), 404
    TransportAssignment.query.filter_by(organization_id=_org_id(), route_id=r.id).delete()
    db.session.delete(r)
    db.session.commit()
    return jsonify({"success": True}), 200


@transport_bp.route("/routes/<int:route_id>/students", methods=["GET"])
@role_required(*_STAFF)
def route_students(route_id):
    r = TransportRoute.query.filter_by(id=route_id, organization_id=_org_id()).first()
    if not r:
        return jsonify({"error": "Route not found"}), 404
    assigns = TransportAssignment.query.filter_by(organization_id=_org_id(), route_id=r.id).all()
    students = {s.id: s for s in Student.query.filter(
        Student.id.in_([a.student_id for a in assigns] or [-1])).all()}
    return jsonify([a.to_dict(student_name=_student_name(students.get(a.student_id)),
                              route_name=r.name) for a in assigns]), 200


@transport_bp.route("/routes/<int:route_id>/students", methods=["POST"])
@role_required(*_STAFF)
def assign_student(route_id):
    r = TransportRoute.query.filter_by(id=route_id, organization_id=_org_id()).first()
    if not r:
        return jsonify({"error": "Route not found"}), 404
    data = request.get_json(silent=True) or {}
    student = Student.query.filter_by(id=data.get("student_id"), organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    existing = TransportAssignment.query.filter_by(
        organization_id=_org_id(), route_id=r.id, student_id=student.id).first()
    if existing:
        existing.stop_name = data.get("stop_name") or existing.stop_name
        db.session.commit()
        return jsonify(existing.to_dict(student_name=_student_name(student), route_name=r.name)), 200
    if r.capacity is not None:
        current = TransportAssignment.query.filter_by(organization_id=_org_id(), route_id=r.id).count()
        if current >= r.capacity:
            return jsonify({"error": "Route is at full capacity"}), 400
    a = TransportAssignment(
        organization_id=_org_id(), route_id=r.id, student_id=student.id,
        stop_name=(data.get("stop_name") or None),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(a.to_dict(student_name=_student_name(student), route_name=r.name)), 201


@transport_bp.route("/assignments/<int:assignment_id>", methods=["DELETE"])
@role_required(*_STAFF)
def unassign(assignment_id):
    a = TransportAssignment.query.filter_by(id=assignment_id, organization_id=_org_id()).first()
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    db.session.delete(a)
    db.session.commit()
    return jsonify({"success": True}), 200


@transport_bp.route("/my", methods=["GET"])
@role_required("student")
def my_transport():
    student = Student.query.filter_by(organization_id=_org_id(), user_id=_user_id()).first()
    if not student:
        return jsonify({"error": "No student record is linked to your account"}), 404
    return student_transport(student.id)


@transport_bp.route("/student/<int:student_id>", methods=["GET"])
@token_required
def student_transport(student_id):
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    role = _role()
    if role in _STAFF or role == "teacher":
        pass
    elif role == "student" and student.user_id == _user_id():
        pass
    elif role == "parent" and Guardian.query.filter_by(
            organization_id=_org_id(), user_id=_user_id(), student_id=student.id).first():
        pass
    else:
        return jsonify({"error": "Not allowed"}), 403

    assigns = TransportAssignment.query.filter_by(organization_id=_org_id(), student_id=student_id).all()
    routes = {r.id: r for r in TransportRoute.query.filter_by(organization_id=_org_id()).all()}
    out = []
    for a in assigns:
        r = routes.get(a.route_id)
        out.append({
            **a.to_dict(student_name=_student_name(student), route_name=r.name if r else None),
            "driver_name": r.driver_name if r else None,
            "driver_phone": r.driver_phone if r else None,
            "vehicle_no": r.vehicle_no if r else None,
        })
    return jsonify({"student": {"id": student.id, "name": _student_name(student)}, "transport": out}), 200
