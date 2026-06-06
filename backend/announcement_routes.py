"""
Announcements / communication API.

Endpoints (under /api/announcements, all tenant-scoped):
  GET    /            List announcements visible to the caller
  POST   /            Create an announcement      (admin/principal/teacher)
  PUT    /<id>        Edit                         (author or admin/principal)
  DELETE /<id>        Delete                       (author or admin/principal)
  GET    /audiences   Audience + class options for the compose form

Audience targeting:
  audience in {all, teachers, students, parents}; an optional batch_id narrows
  a student/parent announcement to a single class. Admins/principals see and
  may post anything; teachers may only post to their own classes.
"""

from flask import Blueprint, request, jsonify

from models import db, Announcement, Batch, Teacher, Student, Guardian, User
from jwt_utils import token_required, role_required

announcement_bp = Blueprint("announcements", __name__, url_prefix="/api/announcements")

VALID_AUDIENCES = {"all", "teachers", "students", "parents"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _org_id():
    user = getattr(request, "user", None)
    return user.get("organization_id") if user else None


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


def _student_batch_id(student):
    b = Batch.query.filter_by(
        organization_id=student.organization_id,
        grade=str(student.class_grade), section=student.section,
    ).first()
    return b.id if b else None


def _caller_batch_ids():
    """Class ids relevant to the caller (for narrowing class-targeted posts)."""
    role = _role()
    if role == "student":
        s = Student.query.filter_by(organization_id=_org_id(), user_id=_user_id()).first()
        bid = _student_batch_id(s) if s else None
        return {bid} if bid else set()
    if role == "parent":
        links = Guardian.query.filter_by(organization_id=_org_id(), user_id=_user_id()).all()
        kids = Student.query.filter(Student.id.in_([g.student_id for g in links] or [-1])).all()
        return {b for b in (_student_batch_id(s) for s in kids) if b}
    teacher = _acting_teacher()
    if teacher:
        return _teacher_batch_ids(teacher)
    return set()


def _visible(ann, role, my_batches):
    """Can a user of `role` (with `my_batches`) see this announcement?"""
    if _is_admin_principal():
        return True
    # Map a role to the audiences it receives.
    role_audiences = {
        "teacher": {"all", "teachers"},
        "coordinator": {"all", "teachers"},
        "student": {"all", "students"},
        "parent": {"all", "parents"},
    }.get(role, {"all"})
    if ann.audience not in role_audiences:
        return False
    # A class-scoped post is only visible to people tied to that class.
    if ann.batch_id is not None and ann.batch_id not in my_batches:
        return False
    return True


# ---------------------------------------------------------------------------
# Compose options
# ---------------------------------------------------------------------------

@announcement_bp.route("/audiences", methods=["GET"])
@role_required("admin", "principal", "coordinator", "teacher")
def audiences():
    org_id = _org_id()
    batches = Batch.query.filter_by(organization_id=org_id).all()
    if not _is_admin_principal():
        teacher = _acting_teacher()
        allowed = _teacher_batch_ids(teacher) if teacher else set()
        batches = [b for b in batches if b.id in allowed]
    batches.sort(key=lambda b: (str(b.grade), b.section))
    return jsonify({
        "audiences": sorted(VALID_AUDIENCES),
        # teachers can only address their own classes; admins org-wide too
        "can_post_org_wide": _is_admin_principal(),
        "classes": [{"batch_id": b.id, "label": f"Grade {b.grade}-{b.section}"} for b in batches],
    }), 200


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@announcement_bp.route("", methods=["GET"])
@token_required
def list_announcements():
    org_id = _org_id()
    role = _role()
    anns = Announcement.query.filter_by(organization_id=org_id).order_by(
        Announcement.created_at.desc()
    ).all()

    my_batches = set() if _is_admin_principal() else _caller_batch_ids()
    visible = [a for a in anns if _visible(a, role, my_batches)]

    author_ids = {a.created_by for a in visible if a.created_by}
    authors = {u.id: u.name for u in User.query.filter(User.id.in_(author_ids or [-1])).all()}
    batch_ids = {a.batch_id for a in visible if a.batch_id}
    batches = {
        b.id: f"Grade {b.grade}-{b.section}"
        for b in Batch.query.filter(Batch.id.in_(batch_ids or [-1])).all()
    }
    return jsonify([
        a.to_dict(author_name=authors.get(a.created_by), batch_label=batches.get(a.batch_id))
        for a in visible
    ]), 200


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@announcement_bp.route("", methods=["POST"])
@role_required("admin", "principal", "coordinator", "teacher")
def create_announcement():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    if not title or not body:
        return jsonify({"error": "Title and message are required"}), 400

    audience = (data.get("audience") or "all").strip()
    if audience not in VALID_AUDIENCES:
        return jsonify({"error": "Invalid audience"}), 400

    batch_id = data.get("batch_id") or None
    if batch_id is not None:
        batch = Batch.query.filter_by(id=batch_id, organization_id=_org_id()).first()
        if not batch:
            return jsonify({"error": "Class not found"}), 400

    # Teachers can only address their own classes — a batch is mandatory and
    # must be one they teach; they cannot post org-wide.
    if not _is_admin_principal():
        teacher = _acting_teacher()
        allowed = _teacher_batch_ids(teacher) if teacher else set()
        if not batch_id or batch_id not in allowed:
            return jsonify({"error": "You can only post to your own classes"}), 403

    ann = Announcement(
        organization_id=_org_id(),
        title=title, body=body, audience=audience,
        batch_id=batch_id, created_by=_user_id(),
    )
    db.session.add(ann)
    db.session.commit()
    author = User.query.get(_user_id())
    return jsonify(ann.to_dict(author_name=author.name if author else None)), 201


# ---------------------------------------------------------------------------
# Edit / delete
# ---------------------------------------------------------------------------

def _owned(ann_id):
    return Announcement.query.filter_by(id=ann_id, organization_id=_org_id()).first()


def _can_modify(ann):
    return _is_admin_principal() or ann.created_by == _user_id()


@announcement_bp.route("/<int:ann_id>", methods=["PUT"])
@role_required("admin", "principal", "coordinator", "teacher")
def update_announcement(ann_id):
    ann = _owned(ann_id)
    if not ann:
        return jsonify({"error": "Announcement not found"}), 404
    if not _can_modify(ann):
        return jsonify({"error": "You cannot edit this announcement"}), 403
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        ann.title = data["title"].strip()
    if "body" in data and data["body"].strip():
        ann.body = data["body"].strip()
    if "audience" in data and data["audience"] in VALID_AUDIENCES:
        ann.audience = data["audience"]
    db.session.commit()
    return jsonify(ann.to_dict()), 200


@announcement_bp.route("/<int:ann_id>", methods=["DELETE"])
@role_required("admin", "principal", "coordinator", "teacher")
def delete_announcement(ann_id):
    ann = _owned(ann_id)
    if not ann:
        return jsonify({"error": "Announcement not found"}), 404
    if not _can_modify(ann):
        return jsonify({"error": "You cannot delete this announcement"}), 403
    db.session.delete(ann)
    db.session.commit()
    return jsonify({"success": True}), 200
