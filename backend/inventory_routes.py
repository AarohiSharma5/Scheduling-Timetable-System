"""
Inventory API (/api/inventory) - admin/principal only.

  GET    /              List items (?category=&low=1 to filter low stock)
  POST   /              Create an item
  PUT    /<id>          Edit an item
  POST   /<id>/adjust   Adjust quantity (body: delta, e.g. +10 or -3)
  DELETE /<id>          Delete an item
  GET    /summary       Counts + low-stock list
"""

from flask import Blueprint, request, jsonify

from models import db, InventoryItem
from jwt_utils import role_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

_STAFF = ("admin", "principal")


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


@inventory_bp.route("", methods=["GET"])
@role_required(*_STAFF)
def list_items():
    q = InventoryItem.query.filter_by(organization_id=_org_id())
    category = request.args.get("category")
    if category:
        q = q.filter_by(category=category)
    items = q.order_by(InventoryItem.name).all()
    if request.args.get("low") == "1":
        items = [i for i in items if i.quantity <= (i.min_quantity or 0)]
    return jsonify([i.to_dict() for i in items]), 200


@inventory_bp.route("", methods=["POST"])
@role_required(*_STAFF)
def create_item():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Item name is required"}), 400
    try:
        qty = int(data.get("quantity") or 0)
        minq = int(data.get("min_quantity") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid quantity"}), 400
    item = InventoryItem(
        organization_id=_org_id(), name=name, category=(data.get("category") or None),
        quantity=max(0, qty), unit=(data.get("unit") or "unit"),
        min_quantity=max(0, minq), location=(data.get("location") or None),
        notes=(data.get("notes") or None),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@inventory_bp.route("/<int:item_id>", methods=["PUT"])
@role_required(*_STAFF)
def update_item(item_id):
    item = InventoryItem.query.filter_by(id=item_id, organization_id=_org_id()).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        item.name = data["name"].strip()
    for field in ("category", "unit", "location", "notes"):
        if field in data:
            setattr(item, field, data[field] or None)
    for field in ("quantity", "min_quantity"):
        if field in data:
            try:
                setattr(item, field, max(0, int(data[field])))
            except (ValueError, TypeError):
                return jsonify({"error": f"Invalid {field}"}), 400
    db.session.commit()
    return jsonify(item.to_dict()), 200


@inventory_bp.route("/<int:item_id>/adjust", methods=["POST"])
@role_required(*_STAFF)
def adjust_item(item_id):
    item = InventoryItem.query.filter_by(id=item_id, organization_id=_org_id()).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta"))
    except (ValueError, TypeError):
        return jsonify({"error": "delta must be an integer"}), 400
    if item.quantity + delta < 0:
        return jsonify({"error": "Adjustment would make quantity negative"}), 400
    item.quantity += delta
    db.session.commit()
    return jsonify(item.to_dict()), 200


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
@role_required(*_STAFF)
def delete_item(item_id):
    item = InventoryItem.query.filter_by(id=item_id, organization_id=_org_id()).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True}), 200


@inventory_bp.route("/summary", methods=["GET"])
@role_required(*_STAFF)
def summary():
    items = InventoryItem.query.filter_by(organization_id=_org_id()).all()
    low = [i for i in items if i.quantity <= (i.min_quantity or 0)]
    return jsonify({
        "item_count": len(items),
        "total_units": sum(i.quantity for i in items),
        "low_stock_count": len(low),
        "low_stock": [i.to_dict() for i in low],
    }), 200
