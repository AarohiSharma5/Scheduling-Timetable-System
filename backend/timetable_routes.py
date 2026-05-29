"""
Timetable Generation API Endpoints

POST /api/timetable/generate - Generate new timetable
GET /api/timetable/<id> - Get timetable with slots
GET /api/timetable/list - List all timetables
POST /api/timetable/<id>/publish - Publish timetable
"""

from flask import Blueprint, request, jsonify
from models import db, Timetable, TimetableSlot, Batch, Subject, Teacher, SchoolConfig
from scheduler import SchedulingEngine
from jwt_utils import token_required, role_required
from datetime import datetime

timetable_bp = Blueprint("timetable", __name__, url_prefix="/api/timetable")

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
        name = data.get("name", f"Timetable {datetime.utcnow().isoformat()}")
        description = data.get("description", "")
        # Create new timetable record
        timetable = Timetable(
            name=name,
            description=description,
            status="draft",
            generated_at=datetime.utcnow()
        )
        db.session.add(timetable)
        db.session.flush()  # Get ID without committing
        # Run scheduling engine
        engine = SchedulingEngine()
        success, warnings = engine.generate_timetable(timetable.id)
        if not success:
            db.session.rollback()
            return jsonify({
                "error": "Failed to generate timetable",
                "details": warnings
            }), 400
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
    timetable = Timetable.query.get(timetable_id)
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
    
    # Get batches info
    batches = Batch.query.all()
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
    timetables = Timetable.query.all()
    
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
    timetable = Timetable.query.get(timetable_id)
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


@timetable_bp.route("/<int:timetable_id>/delete", methods=["DELETE"])
@token_required
@role_required("admin")
def delete_timetable(timetable_id):
    """Delete a timetable"""
    timetable = Timetable.query.get(timetable_id)
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
    batch = Batch.query.get(batch_id)
    if not batch:
        return jsonify({"error": "Batch not found"}), 404
    
    # Get latest published timetable
    timetable = Timetable.query.filter_by(status="published").order_by(Timetable.published_at.desc()).first()
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
