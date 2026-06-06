"""
Academic calendar / holidays API (/api/calendar).

  GET    /          List events (any authenticated user; optional ?year=&type=)
  POST   /          Create event           (admin/principal)
  PUT    /<id>       Update event           (admin/principal)
  DELETE /<id>       Delete event           (admin/principal)
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

from models import db, CalendarEvent
from jwt_utils import token_required, role_required

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")

EVENT_TYPES = {"holiday", "event", "exam", "break", "activity"}


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


def _user_id():
    return (getattr(request, "user", {}) or {}).get("user_id")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@calendar_bp.route("", methods=["GET"])
@token_required
def list_events():
    q = CalendarEvent.query.filter_by(organization_id=_org_id())
    etype = request.args.get("type")
    if etype:
        q = q.filter_by(event_type=etype)
    year = request.args.get("year", type=int)
    events = q.order_by(CalendarEvent.start_date.asc()).all()
    if year:
        events = [e for e in events if e.start_date and e.start_date.year == year]
    return jsonify([e.to_dict() for e in events]), 200


@calendar_bp.route("", methods=["POST"])
@role_required("admin", "principal", "coordinator")
def create_event():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    start = _parse_date(data.get("start_date"))
    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not start:
        return jsonify({"error": "A valid start date is required"}), 400
    etype = data.get("event_type") or "event"
    if etype not in EVENT_TYPES:
        return jsonify({"error": f"event_type must be one of {sorted(EVENT_TYPES)}"}), 400
    end = _parse_date(data.get("end_date"))
    if end and end < start:
        return jsonify({"error": "End date cannot be before start date"}), 400

    ev = CalendarEvent(
        organization_id=_org_id(), title=title, event_type=etype,
        start_date=start, end_date=end, description=(data.get("description") or None),
        created_by=_user_id(),
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify(ev.to_dict()), 201


@calendar_bp.route("/<int:event_id>", methods=["PUT"])
@role_required("admin", "principal", "coordinator")
def update_event(event_id):
    ev = CalendarEvent.query.filter_by(id=event_id, organization_id=_org_id()).first()
    if not ev:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"].strip():
        ev.title = data["title"].strip()
    if "event_type" in data and data["event_type"] in EVENT_TYPES:
        ev.event_type = data["event_type"]
    if "start_date" in data:
        ev.start_date = _parse_date(data["start_date"]) or ev.start_date
    if "end_date" in data:
        ev.end_date = _parse_date(data["end_date"])
    if "description" in data:
        ev.description = data["description"] or None
    db.session.commit()
    return jsonify(ev.to_dict()), 200


@calendar_bp.route("/<int:event_id>", methods=["DELETE"])
@role_required("admin", "principal", "coordinator")
def delete_event(event_id):
    ev = CalendarEvent.query.filter_by(id=event_id, organization_id=_org_id()).first()
    if not ev:
        return jsonify({"error": "Event not found"}), 404
    db.session.delete(ev)
    db.session.commit()
    return jsonify({"success": True}), 200
