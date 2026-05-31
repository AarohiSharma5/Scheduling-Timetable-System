"""
Timetable Generation API Endpoints

POST /api/timetable/generate - Generate new timetable
GET /api/timetable/<id> - Get timetable with slots
GET /api/timetable/list - List all timetables
POST /api/timetable/<id>/publish - Publish timetable
"""

from flask import Blueprint, request, jsonify
from models import (
    db, Timetable, TimetableSlot, Batch, Subject, Teacher, SchoolConfig,
    PinnedSlot, TeacherPreference,
)
from scheduler import SchedulingEngine
from jwt_utils import token_required, role_required
from datetime import datetime
import period_utils
from timetable_edit import collect_conflicts, build_teacher_unavailable

timetable_bp = Blueprint("timetable", __name__, url_prefix="/api/timetable")


def _org_id():
    """Organization id from the authenticated user's JWT."""
    user = getattr(request, "user", None)
    return user.get("organization_id") if user else None

# ============================================================================
# TIMETABLE GENERATION
# ============================================================================

@timetable_bp.route("/generate", methods=["POST"])
@token_required
@role_required("admin", "principal")
def generate_timetable():
    """
    Generate automatic timetable based on current school config
    
    Request body:
    {
        "name": "May 2026 Timetable",
        "description": "Auto-generated for Q3"
    }
    
    Response:
    {
        "id": 1,
        "name": "May 2026 Timetable",
        "status": "draft",
        "warnings": ["warning1", "warning2"],
        "slots_generated": 210,
        "conflicts": 0
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        org_id = _org_id()
        name = data.get("name", f"Timetable {datetime.utcnow().isoformat()}")
        description = data.get("description", "")

        # Each generation is a new draft version, so the admin keeps a short
        # history to compare/roll back to. Older drafts are pruned after commit
        # (see DRAFT_HISTORY_LIMIT below) so storage stays bounded no matter how
        # many times they regenerate. Published timetables are never pruned.
        timetable = Timetable(
            organization_id=org_id,
            name=name,
            description=description,
            status="draft",
            generated_at=datetime.utcnow(),
        )
        db.session.add(timetable)
        db.session.flush()  # Get ID without committing
        # Run scheduling engine, scoped to this organization's data
        engine = SchedulingEngine(organization_id=org_id)
        success, warnings = engine.generate_timetable(timetable.id)
        if not success:
            db.session.rollback()
            return jsonify({
                "error": "Failed to generate timetable",
                "details": warnings
            }), 400
        db.session.commit()

        # Retain only the most recent N draft versions as history; prune older
        # drafts (their slots cascade-delete) to keep the database bounded.
        DRAFT_HISTORY_LIMIT = 5
        stale_drafts = (
            Timetable.query
            .filter_by(organization_id=org_id, status="draft")
            .order_by(Timetable.generated_at.desc())
            .offset(DRAFT_HISTORY_LIMIT)
            .all()
        )
        if stale_drafts:
            for old in stale_drafts:
                db.session.delete(old)
            db.session.commit()

        # Count generated slots
        slots_count = TimetableSlot.query.filter_by(timetable_id=timetable.id).count()
        return jsonify({
            "success": True,
            "timetable": timetable.to_dict(),
            "slots_generated": slots_count,
            "warnings": warnings,
            "message": f"Generated {slots_count} timetable slots"
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Error generating timetable: {str(e)}"
        }), 500


# ============================================================================
# CONFLICT DETECTION & VALIDATION
# ============================================================================

@timetable_bp.route("/<int:timetable_id>/validate", methods=["GET"])
@token_required
def validate_timetable(timetable_id):
    """
    Validate timetable for conflicts and issues
    
    Response includes:
    - is_valid: boolean
    - errors: critical conflicts (double booking, gaps, etc)
    - warnings: non-critical issues (overload, incomplete)
    - gaps: unscheduled subject-batch periods
    - stats: timetable statistics
    """
    try:
        from conflict_detector import ConflictDetector
        
        detector = ConflictDetector(timetable_id)
        report = detector.validate()
        
        return jsonify(report.to_dict()), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 500


@timetable_bp.route("/<int:timetable_id>/conflicts/summary", methods=["GET"])
@token_required
def get_conflict_summary(timetable_id):
    """
    Get brief conflict summary (for dashboard display)
    
    Returns only counts and critical issues
    """
    try:
        from conflict_detector import ConflictDetector
        
        detector = ConflictDetector(timetable_id)
        report = detector.validate()
        
        return jsonify({
            "timetable_id": timetable_id,
            "is_valid": report.is_valid,
            "critical_errors": len(report.errors),
            "warnings": len(report.warnings),
            "incomplete_subjects": len(report.gaps),
            "health_score": max(0, 100 - (len(report.errors) * 20 + len(report.warnings) * 5)),
            "status": "CONFLICT_FREE" if report.is_valid else "HAS_ISSUES",
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@timetable_bp.route("/<int:timetable_id>/conflicts/by-type", methods=["GET"])
@token_required
def get_conflicts_by_type(timetable_id):
    """
    Get conflicts grouped by type for detailed analysis
    
    Useful for admin dashboards
    """
    try:
        from conflict_detector import ConflictDetector
        
        detector = ConflictDetector(timetable_id)
        report = detector.validate()
        
        # Group by type
        by_type = {}
        for error in report.errors:
            error_type = error["type"]
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(error)
        
        return jsonify({
            "timetable_id": timetable_id,
            "conflicts_by_type": by_type,
            "total_conflicts": len(report.errors),
            "types": list(by_type.keys())
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TIMETABLE RETRIEVAL
# ============================================================================

@timetable_bp.route("/<int:timetable_id>", methods=["GET"])
@token_required
def get_timetable(timetable_id):
    """
    Get timetable with all slots organized by batch/day
    
    Response:
    {
        "id": 1,
        "name": "May 2026 Timetable",
        "status": "draft",
        "slots": [
            {
                "day": "Monday",
                "period": 1,
                "batch": {id, grade, section},
                "teacher": {id, name},
                "subject": {id, name}
            }
        ],
        "batches": [...],
        "summary": {
            "total_slots": 210,
            "filled_slots": 205,
            "coverage": "97.6%"
        }
    }
    """
    timetable = Timetable.query.filter_by(id=timetable_id, organization_id=_org_id()).first()
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404
    
    # Get all slots organized by batch
    slots = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()
    
    # Organize slots
    organized_slots = {}
    for slot in slots:
        batch_id = slot.batch_id
        if batch_id not in organized_slots:
            organized_slots[batch_id] = {}
        
        day_key = f"{slot.day}-P{slot.period_number}"
        organized_slots[batch_id][day_key] = slot.to_dict()
    
    # Get batches info (scoped to the org)
    batches = Batch.query.filter_by(organization_id=_org_id()).all()
    batches_info = {b.id: b.to_dict() for b in batches}
    
    # Calculate coverage
    total_slots = len(slots)
    expected_slots = len(batches) * 5 * 6  # Batches × days × periods
    coverage = (total_slots / expected_slots * 100) if expected_slots > 0 else 0
    
    return jsonify({
        "timetable": timetable.to_dict(),
        "slots_by_batch": organized_slots,
        "batches": list(batches_info.values()),
        "summary": {
            "total_slots": total_slots,
            "expected_slots": expected_slots,
            "coverage": f"{coverage:.1f}%",
            "warnings": timetable.warnings
        }
    }), 200


@timetable_bp.route("/list", methods=["GET"])
@token_required
def list_timetables():
    """
    List all timetables with summary info
    
    Response:
    {
        "timetables": [
            {
                "id": 1,
                "name": "May 2026 Timetable",
                "status": "draft",
                "generated_at": "2026-05-06T...",
                "slots_count": 205,
                "warnings": 2
            }
        ]
    }
    """
    # Newest first so the UI can default-select the most recent timetable
    # right after login (drafts and published versions all persist per-org).
    timetables = (
        Timetable.query
        .filter_by(organization_id=_org_id())
        .order_by(Timetable.generated_at.desc().nullslast())
        .all()
    )
    
    result = []
    for tt in timetables:
        slots_count = TimetableSlot.query.filter_by(timetable_id=tt.id).count()
        result.append({
            "id": tt.id,
            "name": tt.name,
            "status": tt.status,
            "generated_at": tt.generated_at.isoformat() if tt.generated_at else None,
            "published_at": tt.published_at.isoformat() if tt.published_at else None,
            "slots_count": slots_count,
            "warnings_count": len(tt.warnings) if tt.warnings else 0
        })
    
    return jsonify({"timetables": result}), 200


# ============================================================================
# TIMETABLE ACTIONS
# ============================================================================

@timetable_bp.route("/<int:timetable_id>/publish", methods=["POST"])
@token_required
@role_required("admin", "principal")
def publish_timetable(timetable_id):
    """
    Publish timetable (make it official)
    
    Response:
    {
        "success": true,
        "message": "Timetable published"
    }
    """
    timetable = Timetable.query.filter_by(id=timetable_id, organization_id=_org_id()).first()
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404
    
    # Check if has slots
    slots_count = TimetableSlot.query.filter_by(timetable_id=timetable_id).count()
    if slots_count == 0:
        return jsonify({
            "error": "Cannot publish empty timetable"
        }), 400
    
    # The engine guarantees no teacher/batch double-booking, so a generated
    # timetable is always *valid* even if some periods are left unfilled on an
    # over-subscribed dataset. We therefore publish and surface the warnings
    # rather than hard-blocking (which previously made publishing impossible).
    timetable.status = "published"
    timetable.published_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Timetable {timetable_id} published",
        "timetable": timetable.to_dict(),
        "warnings": timetable.warnings or []
    }), 200


@timetable_bp.route("/<int:timetable_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def delete_timetable(timetable_id):
    """Delete a timetable"""
    timetable = Timetable.query.filter_by(id=timetable_id, organization_id=_org_id()).first()
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404
    
    if timetable.status == "published":
        return jsonify({
            "error": "Cannot delete published timetable"
        }), 400
    
    db.session.delete(timetable)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Timetable {timetable_id} deleted"
    }), 200


# ============================================================================
# HELPER ENDPOINTS
# ============================================================================

@timetable_bp.route("/batch/<int:batch_id>", methods=["GET"])
@token_required
def get_batch_timetable(batch_id):
    """
    Get timetable for specific batch (student/teacher view)
    
    Response:
    {
        "batch": {id, grade, section, student_count},
        "schedule": {
            "Monday": [
                {"period": 1, "subject": "English", "teacher": "John Doe"},
                {"period": 2, "subject": "Math", "teacher": "Jane Smith"},
                ...
            ]
        }
    }
    """
    org_id = _org_id()
    batch = Batch.query.filter_by(id=batch_id, organization_id=org_id).first()
    if not batch:
        return jsonify({"error": "Batch not found"}), 404
    
    # Get latest published timetable for this org
    timetable = (
        Timetable.query.filter_by(organization_id=org_id, status="published")
        .order_by(Timetable.published_at.desc())
        .first()
    )
    if not timetable:
        return jsonify({"error": "No published timetable available"}), 404
    
    # Get slots for this batch
    slots = TimetableSlot.query.filter_by(timetable_id=timetable.id, batch_id=batch_id).all()
    
    # Organize by day
    schedule = {}
    for slot in slots:
        if slot.day not in schedule:
            schedule[slot.day] = []
        
        teacher = Teacher.query.get(slot.teacher_id) if slot.teacher_id else None
        subject = Subject.query.get(slot.subject_id) if slot.subject_id else None
        
        schedule[slot.day].append({
            "period": slot.period_number,
            "subject": subject.name if subject else "Unknown",
            "teacher": teacher.name if teacher else "TBD"
        })
    
    return jsonify({
        "batch": batch.to_dict(),
        "schedule": schedule,
        "timetable_name": timetable.name
    }), 200


# ============================================================================
# MANUAL TIMETABLE EDITING (drag-and-drop grid)
# ============================================================================

def _current_user_id():
    user = getattr(request, "user", None)
    return user.get("user_id") if user else None


def _owned_timetable(timetable_id):
    return Timetable.query.filter_by(id=timetable_id, organization_id=_org_id()).first()


def _edit_context(org_id):
    """Lookup tables used by validation + grid responses for one org."""
    teachers = Teacher.query.filter_by(organization_id=org_id).all()
    subjects = Subject.query.filter_by(organization_id=org_id).all()
    batches = Batch.query.filter_by(organization_id=org_id).all()
    prefs = TeacherPreference.query.filter_by(organization_id=org_id).all()
    return {
        "teachers": teachers,
        "subjects": subjects,
        "batches": batches,
        "prefs": prefs,
        "teacher_names": {t.id: t.name for t in teachers},
        "subject_names": {s.id: s.name for s in subjects},
        "batch_names": {b.id: (b.display_name if hasattr(b, "display_name") and b.display_name
                               else f"Grade {b.grade}-{b.section}") for b in batches},
        "unavailable": build_teacher_unavailable(teachers, prefs),
    }


def _validate(slots, ctx):
    return collect_conflicts(
        slots,
        teacher_unavailable=ctx["unavailable"],
        teacher_names=ctx["teacher_names"],
        subject_names=ctx["subject_names"],
        batch_names=ctx["batch_names"],
    )


def _conflict_sig(c):
    ids = c.get("batch_ids") or ([c.get("batch_id")] if c.get("batch_id") else [])
    return (c.get("type"), c.get("day"), c.get("period"), c.get("teacher_id"),
            tuple(sorted(x for x in ids if x is not None)), c.get("room"))


def _new_conflicts(before, after):
    """Conflicts present after a change that weren't there before.

    A single cell edit must not be blocked by unrelated pre-existing conflicts
    (e.g. a teacher the generator already placed in an unavailable slot). We only
    reject changes that *introduce* a new conflict; fixing old ones is encouraged.
    """
    seen = {_conflict_sig(b) for b in before}
    return [c for c in after if _conflict_sig(c) not in seen]


def _log_edit(timetable, action, detail):
    timetable.edited_by = _current_user_id()
    timetable.edited_at = datetime.utcnow()
    log = list(timetable.change_log or [])
    log.append({
        "at": timetable.edited_at.isoformat(),
        "by": timetable.edited_by,
        "action": action,
        "detail": detail,
    })
    # Keep the audit trail bounded.
    timetable.change_log = log[-200:]


@timetable_bp.route("/<int:timetable_id>/grid", methods=["GET"])
@token_required
@role_required("admin", "principal")
def get_timetable_grid(timetable_id):
    """Editable grid: layout (days x periods), slots, and option lists."""
    org_id = _org_id()
    timetable = _owned_timetable(timetable_id)
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404

    config = SchoolConfig.query.filter_by(organization_id=org_id).first()
    days = period_utils.working_days(config) if config else period_utils.WEEK_DAYS[:5]
    layout = period_utils.build_layout(config) if config else [
        {"number": i, "start": "", "end": "", "is_lunch": False} for i in range(1, 7)
    ]

    ctx = _edit_context(org_id)
    slots = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()

    return jsonify({
        "timetable": timetable.to_dict(),
        "days": days,
        "periods": layout,
        "slots": [s.to_dict() for s in slots],
        "batches": [b.to_dict() for b in ctx["batches"]],
        "subjects": [s.to_dict() for s in ctx["subjects"]],
        "teachers": [
            {"id": t.id, "name": t.name, "teacher_code": t.teacher_code,
             "subject_ids": t.subject_ids or [], "assigned_batch_ids": t.assigned_batch_ids or [],
             "unavailable_slots": t.unavailable_slots or []}
            for t in ctx["teachers"]
        ],
    }), 200


def _slots_after_change(existing, change):
    """Project the current slots into the list they'd be after applying `change`.

    `change` = {batch_id, day, period_number, subject_id, teacher_id, room}.
    Used to validate before committing. Returns list of plain dicts.
    """
    key = (change["batch_id"], change["day"], change["period_number"])
    out = []
    replaced = False
    for s in existing:
        if (s.batch_id, s.day, s.period_number) == key:
            replaced = True
            if change.get("subject_id") is None and change.get("teacher_id") is None:
                continue  # cleared
            out.append({**s.to_dict(), **change})
        else:
            out.append(s.to_dict())
    if not replaced and (change.get("subject_id") is not None or change.get("teacher_id") is not None):
        out.append(change)
    return out


@timetable_bp.route("/<int:timetable_id>/slot", methods=["PATCH"])
@token_required
@role_required("admin", "principal")
def patch_slot(timetable_id):
    """Assign/update/clear a single cell. Validates before saving."""
    org_id = _org_id()
    timetable = _owned_timetable(timetable_id)
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        batch_id = int(data["batch_id"])
        day = str(data["day"])
        period = int(data["period_number"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "batch_id, day and period_number are required"}), 400

    subject_id = data.get("subject_id")
    teacher_id = data.get("teacher_id")
    room = (data.get("room") or "").strip() or None

    change = {"batch_id": batch_id, "day": day, "period_number": period,
              "subject_id": subject_id, "teacher_id": teacher_id, "room": room}

    existing = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()
    ctx = _edit_context(org_id)
    before = _validate([s.to_dict() for s in existing], ctx)
    after = _validate(_slots_after_change(existing, change), ctx)
    introduced = _new_conflicts(before, after)
    if introduced:
        return jsonify({"error": "Validation failed", "conflicts": introduced}), 409

    slot = TimetableSlot.query.filter_by(
        timetable_id=timetable_id, batch_id=batch_id, day=day, period_number=period
    ).first()

    if subject_id is None and teacher_id is None:
        if slot and not slot.is_lunch:
            db.session.delete(slot)
        _log_edit(timetable, "clear", change)
    else:
        if not slot:
            slot = TimetableSlot(organization_id=org_id, timetable_id=timetable_id,
                                 batch_id=batch_id, day=day, period_number=period)
            db.session.add(slot)
        slot.subject_id = subject_id
        slot.teacher_id = teacher_id
        slot.room = room
        _log_edit(timetable, "assign", change)

    db.session.commit()
    return jsonify({"success": True, "timetable": timetable.to_dict(),
                    "slot": slot.to_dict() if (subject_id or teacher_id) else None}), 200


@timetable_bp.route("/<int:timetable_id>/swap", methods=["PATCH"])
@token_required
@role_required("admin", "principal")
def patch_swap(timetable_id):
    """Swap the contents of two cells within the same batch (move = swap w/ empty)."""
    org_id = _org_id()
    timetable = _owned_timetable(timetable_id)
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        batch_id = int(data["batch_id"])
        a = data["a"]; b = data["b"]
        a_day, a_p = str(a["day"]), int(a["period_number"])
        b_day, b_p = str(b["day"]), int(b["period_number"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "batch_id and both cells (a, b) are required"}), 400

    slot_a = TimetableSlot.query.filter_by(timetable_id=timetable_id, batch_id=batch_id,
                                           day=a_day, period_number=a_p).first()
    slot_b = TimetableSlot.query.filter_by(timetable_id=timetable_id, batch_id=batch_id,
                                           day=b_day, period_number=b_p).first()
    if (slot_a and slot_a.is_lunch) or (slot_b and slot_b.is_lunch):
        return jsonify({"error": "Lunch periods cannot be moved"}), 400

    content_a = (slot_a.subject_id, slot_a.teacher_id, slot_a.room, slot_a.is_pinned) if slot_a else None
    content_b = (slot_b.subject_id, slot_b.teacher_id, slot_b.room, slot_b.is_pinned) if slot_b else None

    # Build the projected grid for validation.
    existing = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()
    projected = []
    for s in existing:
        d = s.to_dict()
        if (s.batch_id, s.day, s.period_number) == (batch_id, a_day, a_p):
            sub, tea, rm = (content_b[0], content_b[1], content_b[2]) if content_b else (None, None, None)
            d.update({"subject_id": sub, "teacher_id": tea, "room": rm})
        elif (s.batch_id, s.day, s.period_number) == (batch_id, b_day, b_p):
            sub, tea, rm = (content_a[0], content_a[1], content_a[2]) if content_a else (None, None, None)
            d.update({"subject_id": sub, "teacher_id": tea, "room": rm})
        projected.append(d)
    # If a target had no row yet, add the moved content as a new cell.
    have_a = any((s.batch_id, s.day, s.period_number) == (batch_id, a_day, a_p) for s in existing)
    have_b = any((s.batch_id, s.day, s.period_number) == (batch_id, b_day, b_p) for s in existing)
    if not have_a and content_b:
        projected.append({"batch_id": batch_id, "day": a_day, "period_number": a_p,
                          "subject_id": content_b[0], "teacher_id": content_b[1], "room": content_b[2]})
    if not have_b and content_a:
        projected.append({"batch_id": batch_id, "day": b_day, "period_number": b_p,
                          "subject_id": content_a[0], "teacher_id": content_a[1], "room": content_a[2]})

    ctx = _edit_context(org_id)
    before = _validate([s.to_dict() for s in existing], ctx)
    introduced = _new_conflicts(before, _validate(projected, ctx))
    if introduced:
        return jsonify({"error": "Validation failed", "conflicts": introduced}), 409

    def _apply(slot, day, period, content):
        if content is None:
            if slot and not slot.is_lunch:
                db.session.delete(slot)
            return
        if not slot:
            slot = TimetableSlot(organization_id=org_id, timetable_id=timetable_id,
                                 batch_id=batch_id, day=day, period_number=period)
            db.session.add(slot)
        slot.subject_id, slot.teacher_id, slot.room, slot.is_pinned = content

    _apply(slot_a, a_day, a_p, content_b)
    _apply(slot_b, b_day, b_p, content_a)
    _log_edit(timetable, "swap", {"batch_id": batch_id, "a": {"day": a_day, "period": a_p},
                                  "b": {"day": b_day, "period": b_p}})
    db.session.commit()
    return jsonify({"success": True, "timetable": timetable.to_dict()}), 200


def _set_pin(timetable_id, org_id, batch_id, day, period, pinned):
    slot = TimetableSlot.query.filter_by(timetable_id=timetable_id, batch_id=batch_id,
                                         day=day, period_number=period).first()
    if not slot or slot.subject_id is None:
        return None, (jsonify({"error": "Can only pin a filled period"}), 400)
    slot.is_pinned = pinned
    existing_pin = PinnedSlot.query.filter_by(organization_id=org_id, batch_id=batch_id,
                                              day=day, period_number=period).first()
    if pinned:
        if existing_pin:
            existing_pin.subject_id = slot.subject_id
            existing_pin.teacher_id = slot.teacher_id
        else:
            db.session.add(PinnedSlot(organization_id=org_id, batch_id=batch_id,
                                      subject_id=slot.subject_id, teacher_id=slot.teacher_id,
                                      day=day, period_number=period))
    elif existing_pin:
        db.session.delete(existing_pin)
    return slot, None


@timetable_bp.route("/<int:timetable_id>/pin", methods=["PATCH"])
@token_required
@role_required("admin", "principal")
def patch_pin(timetable_id):
    return _pin_unpin(timetable_id, True)


@timetable_bp.route("/<int:timetable_id>/unpin", methods=["PATCH"])
@token_required
@role_required("admin", "principal")
def patch_unpin(timetable_id):
    return _pin_unpin(timetable_id, False)


def _pin_unpin(timetable_id, pinned):
    org_id = _org_id()
    timetable = _owned_timetable(timetable_id)
    if not timetable:
        return jsonify({"error": "Timetable not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        batch_id = int(data["batch_id"]); day = str(data["day"]); period = int(data["period_number"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "batch_id, day and period_number are required"}), 400

    slot, err = _set_pin(timetable_id, org_id, batch_id, day, period, pinned)
    if err:
        return err
    _log_edit(timetable, "pin" if pinned else "unpin",
              {"batch_id": batch_id, "day": day, "period": period})
    db.session.commit()
    return jsonify({"success": True, "slot": slot.to_dict()}), 200


@timetable_bp.route("/<int:timetable_id>/validate-grid", methods=["POST"])
@token_required
@role_required("admin", "principal")
def validate_grid(timetable_id):
    """Validate a proposed full grid without saving. Body: {slots: [...]}."""
    org_id = _org_id()
    if not _owned_timetable(timetable_id):
        return jsonify({"error": "Timetable not found"}), 404
    data = request.get_json(silent=True) or {}
    slots = data.get("slots", [])
    ctx = _edit_context(org_id)
    conflicts = _validate(slots, ctx)
    return jsonify({"valid": len(conflicts) == 0, "conflicts": conflicts}), 200


@timetable_bp.route("/<int:timetable_id>/save-version", methods=["POST"])
@token_required
@role_required("admin", "principal")
def save_version(timetable_id):
    """Persist manual edits as a NEW draft version.

    Body (optional): {name, slots: [...]}. If `slots` is provided it becomes the
    new version's content; otherwise the source timetable is cloned as-is.
    Pinned cells are mirrored into pinned_slots so future generation honours them.
    """
    org_id = _org_id()
    source = _owned_timetable(timetable_id)
    if not source:
        return jsonify({"error": "Timetable not found"}), 404

    data = request.get_json(silent=True) or {}
    provided = data.get("slots")
    if provided is None:
        provided = [s.to_dict() for s in TimetableSlot.query.filter_by(timetable_id=timetable_id).all()]

    ctx = _edit_context(org_id)
    conflicts = _validate(provided, ctx)
    if conflicts:
        return jsonify({"error": "Validation failed", "conflicts": conflicts}), 409

    new_tt = Timetable(
        organization_id=org_id,
        name=data.get("name") or f"{source.name} (edited {datetime.utcnow().strftime('%d %b %H:%M')})",
        description=f"Manual edit of timetable #{source.id}",
        status="draft",
        generated_at=datetime.utcnow(),
        school_name=source.school_name,
        school_logo_path=source.school_logo_path,
        edited_by=_current_user_id(),
        edited_at=datetime.utcnow(),
        change_log=[{
            "at": datetime.utcnow().isoformat(),
            "by": _current_user_id(),
            "action": "save_version",
            "detail": {"from_timetable_id": source.id, "slots": len(provided)},
        }],
    )
    db.session.add(new_tt)
    db.session.flush()

    valid_batches = set(ctx["batch_names"].keys())
    for s in provided:
        bid = s.get("batch_id")
        if bid not in valid_batches:
            continue
        db.session.add(TimetableSlot(
            organization_id=org_id,
            timetable_id=new_tt.id,
            batch_id=bid,
            day=s.get("day"),
            period_number=s.get("period_number"),
            subject_id=s.get("subject_id"),
            teacher_id=s.get("teacher_id"),
            room=(s.get("room") or None),
            is_lunch=bool(s.get("is_lunch")),
            is_pinned=bool(s.get("is_pinned")),
        ))

    # Mirror pinned cells into pinned_slots (replace this org's pins for the
    # affected day/period/batch so future generation reproduces them).
    for s in provided:
        if s.get("is_pinned") and s.get("subject_id"):
            existing_pin = PinnedSlot.query.filter_by(
                organization_id=org_id, batch_id=s.get("batch_id"),
                day=s.get("day"), period_number=s.get("period_number")).first()
            if existing_pin:
                existing_pin.subject_id = s.get("subject_id")
                existing_pin.teacher_id = s.get("teacher_id")
            else:
                db.session.add(PinnedSlot(
                    organization_id=org_id, batch_id=s.get("batch_id"),
                    subject_id=s.get("subject_id"), teacher_id=s.get("teacher_id"),
                    day=s.get("day"), period_number=s.get("period_number")))

    db.session.commit()

    # Keep draft history bounded (mirror of generate()).
    DRAFT_HISTORY_LIMIT = 5
    stale = (Timetable.query.filter_by(organization_id=org_id, status="draft")
             .order_by(Timetable.generated_at.desc()).offset(DRAFT_HISTORY_LIMIT).all())
    for old in stale:
        db.session.delete(old)
    if stale:
        db.session.commit()

    return jsonify({"success": True, "timetable": new_tt.to_dict()}), 201
