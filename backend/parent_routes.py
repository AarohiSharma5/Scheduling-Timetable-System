"""
Parent accounts + parent self-service API.

Admin/principal provisioning (under /api):
  GET    /admin/parents          List parent accounts + their children
  POST   /admin/parents          Create a parent account linked to students
  DELETE /admin/parents/<id>     Remove a parent account + its links

Parent self-service:
  GET    /parent/children        The logged-in parent's children (with class)

Child attendance/exam history is served by the existing
/api/attendance/student/<id> and /api/exams/student/<id> endpoints, which are
extended to authorize a parent for their own children.
"""

import secrets

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash

from models import db, User, Student, Guardian, Batch
from jwt_utils import token_required, role_required

parent_bp = Blueprint("parents", __name__, url_prefix="/api")


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


def _user_id():
    return (getattr(request, "user", {}) or {}).get("user_id")


def _gen_temp_password():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz"
    digits = "23456789"
    return ("".join(secrets.choice(alphabet) for _ in range(6))
            + "".join(secrets.choice(digits) for _ in range(3)))


def _child_dict(student):
    return {
        "student_id": student.id,
        "name": f"{student.first_name} {student.last_name}".strip(),
        "class": f"{student.class_grade}-{student.section}",
        "roll_no": student.roll_no,
    }


# ---------------------------------------------------------------------------
# Admin provisioning
# ---------------------------------------------------------------------------

@parent_bp.route("/admin/parents", methods=["GET"])
@role_required("admin", "principal")
def list_parents():
    org_id = _org_id()
    parents = User.query.filter_by(organization_id=org_id, role="parent").order_by(User.name).all()
    links = Guardian.query.filter_by(organization_id=org_id).all()
    by_parent = {}
    for g in links:
        by_parent.setdefault(g.user_id, []).append(g.student_id)

    all_sids = [sid for sids in by_parent.values() for sid in sids]
    students = {s.id: s for s in Student.query.filter(Student.id.in_(all_sids or [-1])).all()}

    out = []
    for p in parents:
        kids = [students[sid] for sid in by_parent.get(p.id, []) if sid in students]
        out.append({
            "id": p.id, "name": p.name, "email": p.email, "phone": p.phone,
            "status": p.status,
            "children": [_child_dict(s) for s in kids],
        })
    return jsonify(out), 200


@parent_bp.route("/admin/parents", methods=["POST"])
@role_required("admin", "principal")
def create_parent():
    org_id = _org_id()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    student_ids = data.get("student_ids") or []

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400
    if not isinstance(student_ids, list) or not student_ids:
        return jsonify({"error": "Link at least one student"}), 400

    if User.query.filter_by(email=email, organization_id=org_id).first():
        return jsonify({"error": "A user with this email already exists"}), 409

    students = Student.query.filter(
        Student.organization_id == org_id, Student.id.in_(student_ids)
    ).all()
    if len(students) != len(set(student_ids)):
        return jsonify({"error": "One or more students were not found"}), 400

    provided_pw = data.get("password")
    raw_password = provided_pw or _gen_temp_password()
    is_temp = not provided_pw

    parent = User(
        organization_id=org_id, name=name, email=email, role="parent",
        phone=(data.get("phone") or None),
        password_hash=generate_password_hash(raw_password),
        status="active", must_change_password=is_temp,
        profile_completed=not is_temp, created_by_id=_user_id(),
    )
    db.session.add(parent)
    db.session.flush()

    relation = (data.get("relation") or "guardian").strip() or "guardian"
    for s in students:
        db.session.add(Guardian(
            organization_id=org_id, user_id=parent.id,
            student_id=s.id, relation=relation,
        ))
    db.session.commit()

    return jsonify({
        "id": parent.id, "name": parent.name, "email": parent.email,
        "children": [_child_dict(s) for s in students],
        "credentials": {
            "email": parent.email,
            "temporary_password": raw_password if is_temp else None,
            "must_change_password": is_temp,
        },
    }), 201


@parent_bp.route("/admin/parents/<int:parent_id>", methods=["DELETE"])
@role_required("admin", "principal")
def delete_parent(parent_id):
    org_id = _org_id()
    parent = User.query.filter_by(id=parent_id, organization_id=org_id, role="parent").first()
    if not parent:
        return jsonify({"error": "Parent not found"}), 404
    Guardian.query.filter_by(organization_id=org_id, user_id=parent.id).delete()
    db.session.delete(parent)
    db.session.commit()
    return jsonify({"success": True}), 200


# ---------------------------------------------------------------------------
# Parent self-service
# ---------------------------------------------------------------------------

@parent_bp.route("/parent/children", methods=["GET"])
@role_required("parent")
def my_children():
    org_id = _org_id()
    links = Guardian.query.filter_by(organization_id=org_id, user_id=_user_id()).all()
    students = Student.query.filter(
        Student.organization_id == org_id,
        Student.id.in_([g.student_id for g in links] or [-1]),
    ).all()
    return jsonify([_child_dict(s) for s in students]), 200
