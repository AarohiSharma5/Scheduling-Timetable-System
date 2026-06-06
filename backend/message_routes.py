"""
Direct messaging API (/api/messages) - 1:1 messages within an organization.

  GET  /directory          Users the caller is allowed to message
  GET  /conversations      Conversation partners + last message + unread count
  GET  /thread/<user_id>   Full thread with a user (marks incoming as read)
  POST /                    Send a message (body: recipient_id, body)
  GET  /unread-count       Total unread messages (for a badge)

Rules: staff (admin/principal/teacher) can message anyone in the org;
parents/students can only message staff. All scoped to one organization.
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

from models import db, Message, User
from jwt_utils import token_required

message_bp = Blueprint("messages", __name__, url_prefix="/api/messages")

_STAFF = {"owner", "admin", "principal", "coordinator", "teacher"}


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


def _user_id():
    return (getattr(request, "user", {}) or {}).get("user_id")


def _role():
    return (getattr(request, "user", {}) or {}).get("role")


def _can_message(target):
    if not target or target.organization_id != _org_id() or target.id == _user_id():
        return False
    # Staff can reach anyone; non-staff can only reach staff.
    return _role() in _STAFF or target.role in _STAFF


@message_bp.route("/directory", methods=["GET"])
@token_required
def directory():
    users = User.query.filter(User.organization_id == _org_id(), User.id != _user_id()).all()
    if _role() not in _STAFF:
        users = [u for u in users if u.role in _STAFF]
    users.sort(key=lambda u: (u.role, (u.name or "").lower()))
    return jsonify([{"id": u.id, "name": u.name, "role": u.role} for u in users]), 200


@message_bp.route("/conversations", methods=["GET"])
@token_required
def conversations():
    me = _user_id()
    msgs = Message.query.filter(
        Message.organization_id == _org_id(),
        db.or_(Message.sender_id == me, Message.recipient_id == me),
    ).order_by(Message.created_at.desc()).all()

    partners = {}
    for m in msgs:
        other = m.recipient_id if m.sender_id == me else m.sender_id
        if other not in partners:
            partners[other] = {"last": m, "unread": 0}
        if m.recipient_id == me and m.read_at is None:
            partners[other]["unread"] += 1

    users = {u.id: u for u in User.query.filter(
        User.id.in_(list(partners.keys()) or [-1])).all()}
    out = []
    for other, info in partners.items():
        u = users.get(other)
        last = info["last"]
        out.append({
            "user_id": other,
            "name": u.name if u else "Unknown",
            "role": u.role if u else None,
            "last_message": last.body,
            "last_at": last.created_at.isoformat() if last.created_at else None,
            "unread": info["unread"],
        })
    out.sort(key=lambda c: c["last_at"] or "", reverse=True)
    return jsonify(out), 200


@message_bp.route("/thread/<int:user_id>", methods=["GET"])
@token_required
def thread(user_id):
    other = User.query.filter_by(id=user_id, organization_id=_org_id()).first()
    if not other:
        return jsonify({"error": "User not found"}), 404
    me = _user_id()
    msgs = Message.query.filter(
        Message.organization_id == _org_id(),
        db.or_(
            db.and_(Message.sender_id == me, Message.recipient_id == user_id),
            db.and_(Message.sender_id == user_id, Message.recipient_id == me),
        ),
    ).order_by(Message.created_at.asc()).all()

    # Mark incoming as read.
    now = datetime.utcnow()
    changed = False
    for m in msgs:
        if m.recipient_id == me and m.read_at is None:
            m.read_at = now
            changed = True
    if changed:
        db.session.commit()

    return jsonify({
        "partner": {"id": other.id, "name": other.name, "role": other.role},
        "messages": [m.to_dict(my_user_id=me) for m in msgs],
    }), 200


@message_bp.route("", methods=["POST"])
@token_required
def send_message():
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Message body is required"}), 400
    target = User.query.filter_by(id=data.get("recipient_id"), organization_id=_org_id()).first()
    if not _can_message(target):
        return jsonify({"error": "You cannot message this user"}), 403
    m = Message(
        organization_id=_org_id(), sender_id=_user_id(), recipient_id=target.id, body=body,
    )
    db.session.add(m)
    db.session.commit()
    return jsonify(m.to_dict(my_user_id=_user_id())), 201


@message_bp.route("/unread-count", methods=["GET"])
@token_required
def unread_count():
    count = Message.query.filter_by(
        organization_id=_org_id(), recipient_id=_user_id(), read_at=None).count()
    return jsonify({"unread": count}), 200
