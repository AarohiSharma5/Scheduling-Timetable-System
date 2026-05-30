"""
API Routes for School Timetable Scheduling System

Endpoints organized by module:
- /api/auth/* - Authentication
- /api/admin/* - Admin management (teachers, batches, subjects, config)
- /api/timetable/* - Timetable generation and access
- /api/teacher/* - Teacher views
- /api/student/* - Student views
- /api/principal/* - Principal dashboard
"""

from flask import Blueprint, request, jsonify, abort
from models import db, User, Batch, Subject, Teacher, SchoolConfig, Timetable, TimetableSlot, LeaveRequest, Notification, Organization
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from jwt_utils import (
    generate_token,
    verify_token,
    get_token_from_request,
    token_required,
    role_required,
    generate_org_token,
    verify_org_token,
    get_org_token_from_request,
)
import os

api = Blueprint("api", __name__, url_prefix="/api")


def current_org_id():
    """Organization id from the authenticated user's JWT.

    Populated by the token_required / role_required decorators. Every
    tenant-facing query must filter on this so one organization can never see
    or mutate another's data.
    """
    user = getattr(request, "user", None)
    return user.get("organization_id") if user else None


def owned_or_404(model, obj_id):
    """Fetch a record by id but only if it belongs to the caller's org."""
    obj = model.query.filter_by(id=obj_id, organization_id=current_org_id()).first()
    if obj is None:
        abort(404)
    return obj

# ============================================================================
# HEALTH CHECK
# ============================================================================

def get_db_stats():
    """Helper to get database statistics"""
    return {
        "users": User.query.count(),
        "batches": Batch.query.count(),
        "subjects": Subject.query.count(),
        "teachers": Teacher.query.count(),
        "timetables": Timetable.query.count(),
    }


@api.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "API is running",
        "timestamp": datetime.utcnow().isoformat(),
        "db_stats": get_db_stats(),
    }), 200


# ============================================================================
# ORGANIZATION ENDPOINTS
# ============================================================================

def _resolve_org_from_request():
    """Validate the X-Org-Token header and return the Organization, or (None, error_response)."""
    token = get_org_token_from_request()
    if not token:
        return None, (jsonify({"error": "Organization session required"}), 401)
    payload = verify_org_token(token)
    if "error" in payload:
        return None, (jsonify(payload), 401)
    org = Organization.query.get(payload.get("organization_id"))
    if not org:
        return None, (jsonify({"error": "Organization no longer exists"}), 404)
    return org, None


@api.route("/organizations/login", methods=["POST"])
def organization_login():
    """
    Authenticate an organization (tenant) before user login.
    Body: { "identifier": "test-sample-institute" | "Test Sample Institute", "password": "..." }
    Returns: { "org_token": "...", "organization": {...} }
    """
    try:
        data = request.get_json() or {}
        identifier = (data.get("identifier") or data.get("name") or data.get("slug") or "").strip()
        password = (data.get("password") or "").strip()

        if not identifier or not password:
            return jsonify({"error": "Organization name and password are required"}), 400

        slug = identifier.lower().replace(" ", "-")
        org = (
            Organization.query.filter_by(slug=slug).first()
            or Organization.query.filter(db.func.lower(Organization.name) == identifier.lower()).first()
        )
        if not org or not check_password_hash(org.password_hash, password):
            return jsonify({"error": "Invalid organization or password"}), 401

        token = generate_org_token(org.id, org.slug)
        return jsonify({
            "org_token": token,
            "organization": org.to_dict(),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/organizations/me", methods=["GET"])
def organization_me():
    """Return the organization associated with the current X-Org-Token header."""
    org, err = _resolve_org_from_request()
    if err:
        return err
    return jsonify(org.to_dict()), 200


@api.route("/organizations/list", methods=["GET"])
def organizations_list():
    """Public list of organization names/slugs (no auth) to populate the login dropdown."""
    orgs = Organization.query.order_by(Organization.name.asc()).all()
    return jsonify([{"id": o.id, "name": o.name, "slug": o.slug, "logo_url": o.logo_url} for o in orgs]), 200


# ============================================================================
# AUTH ENDPOINTS (Step 2)
# ============================================================================

@api.route("/auth/login", methods=["POST"])
def login():
    """
    Login endpoint (requires X-Org-Token header from a prior /organizations/login).
    Body: { "email": "user@school.edu", "password": "password" }
    Returns: { "token": "jwt_token", "user": {...} }
    """
    try:
        org, err = _resolve_org_from_request()
        if err:
            return err

        data = request.get_json()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

        # Enforce that user belongs to the organization they're logging into.
        if user.organization_id is not None and user.organization_id != org.id:
            return jsonify({"error": "This account does not belong to the selected organization"}), 403

        token = generate_token(user.id, user.email, user.role, organization_id=org.id)

        return jsonify({
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "batch_id": user.batch_id,
                "organization_id": org.id,
            },
            "organization": org.to_dict(),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/auth/logout", methods=["POST"])
def logout():
    """Logout endpoint (token invalidation handled by frontend)"""
    return jsonify({"message": "Logged out"}), 200


@api.route("/auth/me", methods=["GET"])
@token_required
def get_current_user():
    """Get current authenticated user info"""
    try:
        user = User.query.get(request.user.get("user_id"))
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get additional info based on role
        additional_info = {}
        if user.role == "teacher":
            teacher = Teacher.query.filter_by(user_id=user.id).first()
            if teacher:
                additional_info["teacher_id"] = teacher.id
                additional_info["assigned_batches"] = teacher.assigned_batch_ids
                additional_info["subjects"] = teacher.subject_ids
        elif user.role == "student":
            additional_info["batch_id"] = user.batch_id
        
        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "batch_id": user.batch_id,
            **additional_info,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PLANS ENDPOINTS - Timetable Plans (Frontend Format)
# ============================================================================

def format_timetable_as_plan(timetable):
    """Convert Timetable object to Plan format for frontend"""
    config = SchoolConfig.query.first() or SchoolConfig()
    
    # Build per-batch timetable grids
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    periods_per_day = config.periods_per_day
    days_per_week = config.working_days

    # Lookups (avoids a DB query per slot when building grids), scoped to the
    # timetable's own organization.
    org_id = timetable.organization_id
    all_teachers = Teacher.query.filter_by(organization_id=org_id).all()
    all_subjects = Subject.query.filter_by(organization_id=org_id).all()
    all_batches = Batch.query.filter_by(organization_id=org_id).all()
    teacher_by_id = {t.id: t for t in all_teachers}
    subject_by_id = {s.id: s for s in all_subjects}
    batch_by_id = {b.id: b for b in all_batches}

    def batch_label(batch):
        return f"Grade {batch.grade} - {batch.section}" if batch else "Unknown"

    # Group slots per batch so grids don't overwrite each other across batches.
    slots = TimetableSlot.query.filter_by(timetable_id=timetable.id).all()
    per_batch_slots = {}  # batch_id -> {(day, period_number): slot}
    for slot in slots:
        per_batch_slots.setdefault(slot.batch_id, {})[(slot.day, slot.period_number)] = slot

    def build_grid(slot_map):
        grid = []
        for day_name in days:
            day_row = []
            for period_idx in range(periods_per_day):
                slot = slot_map.get((day_name, period_idx + 1))
                if slot and not slot.is_lunch and slot.teacher_id:
                    teacher = teacher_by_id.get(slot.teacher_id)
                    subject = subject_by_id.get(slot.subject_id)
                    batch = batch_by_id.get(slot.batch_id)
                    day_row.append({
                        "subject": subject.name if subject else "Unknown",
                        "teacher": teacher.name if teacher else "Unknown",
                        "subject_id": slot.subject_id,
                        "teacher_id": slot.teacher_id,
                        "batch_id": slot.batch_id,
                        "batch_name": batch_label(batch),
                        "is_lunch": False,
                    })
                else:
                    day_row.append(None)  # Lunch or free period
            grid.append(day_row)
        return grid

    batch_timetables = [
        {
            "batch_id": batch_id,
            "batch_name": batch_label(batch_by_id.get(batch_id)),
            "timetable": build_grid(per_batch_slots[batch_id]),
        }
        for batch_id in sorted(per_batch_slots.keys(), key=lambda x: (x is None, x))
    ]

    # Backward-compatible single grid = first batch (or an empty grid).
    timetable_array = (
        batch_timetables[0]["timetable"]
        if batch_timetables
        else [[None for _ in range(periods_per_day)] for _ in days]
    )

    # Resolve the institution name from the organization (single tenant) or the
    # timetable's own school_name, falling back to a generic label.
    organization = Organization.query.first()
    institution_name = (
        (organization.name if organization else None)
        or timetable.school_name
        or "School"
    )

    # Total student headcount derived from batch sizes.
    student_count = sum((b.student_count or 0) for b in all_batches)

    # Map each subject to a teacher who actually teaches it (first eligible).
    subject_teacher_map = {}
    for t in all_teachers:
        for sid in (t.subject_ids or []):
            subject_teacher_map.setdefault(sid, t.id)

    return {
        "id": timetable.id,
        "title": timetable.name,
        "description": timetable.description,
        "status": timetable.status if timetable.status in ["draft", "completed"] else "completed",
        "school_profile": {
            "institution_name": institution_name,
            "days_per_week": days_per_week,
            "periods_per_day": periods_per_day,
            "student_count": student_count,
            "core_subjects_target": len(all_subjects),
            "elective_limit": max(len(all_subjects) - 5, 0),
        },
        "teachers": [
            {
                "id": t.id,
                "name": t.name,
                "contact_hours": t.max_periods_per_week or 24,
                "expertise": [subject_by_id[sid].name for sid in (t.subject_ids or []) if sid in subject_by_id],
            }
            for t in all_teachers
        ],
        "subjects": [
            {
                "id": s.id,
                "name": s.name,
                "teacher_id": subject_teacher_map.get(s.id),
                "is_core": True,
                "periods_required": s.periods_per_week,
            }
            for s in all_subjects
        ],
        "timetable": timetable_array,
        "batch_timetables": batch_timetables,
        "warnings": timetable.warnings or [],
        "created_at": timetable.created_at.isoformat() if timetable.created_at else None,
        "updated_at": timetable.updated_at.isoformat() if timetable.updated_at else None,
    }


@api.route("/plans", methods=["GET"])
@token_required
def get_plans():
    """Get the caller organization's published plans/timetables"""
    try:
        org_id = current_org_id()
        # Get published timetables for this org
        timetables = Timetable.query.filter_by(
            organization_id=org_id, status="published"
        ).all()
        
        if not timetables:
            # Fall back to the org's most recent timetable if none published
            timetables = (
                Timetable.query.filter_by(organization_id=org_id)
                .order_by(Timetable.generated_at.desc())
                .limit(1)
                .all()
            )
        
        plans = [format_timetable_as_plan(t) for t in timetables]
        return jsonify(plans), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/plans/<int:timetable_id>", methods=["GET"])
@token_required
def get_plan(timetable_id):
    """Get a specific plan/timetable owned by the caller's org"""
    try:
        timetable = Timetable.query.filter_by(
            id=timetable_id, organization_id=current_org_id()
        ).first()
        if not timetable:
            return jsonify({"error": "Plan not found"}), 404
        
        plan = format_timetable_as_plan(timetable)
        return jsonify(plan), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ANALYTICS ENDPOINTS - Principal Analytics
# ============================================================================

@api.route("/analytics/<int:timetable_id>", methods=["GET"])
@role_required("principal", "admin")
def get_timetable_analytics(timetable_id):
    """Get comprehensive timetable analytics"""
    try:
        org_id = current_org_id()
        timetable = Timetable.query.filter_by(id=timetable_id, organization_id=org_id).first()
        if not timetable:
            return jsonify({"error": "Timetable not found"}), 404

        teachers = Teacher.query.filter_by(organization_id=org_id).all()
        batches = Batch.query.filter_by(organization_id=org_id).all()
        subjects = Subject.query.filter_by(organization_id=org_id).all()
        config = SchoolConfig.query.filter_by(organization_id=org_id).first() or SchoolConfig()

        # Get all slots for this timetable
        slots = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()
        
        # Calculate teacher analytics
        teacher_analytics = []
        for teacher in teachers:
            teacher_slots = [s for s in slots if s.teacher_id == teacher.id and not s.is_lunch]
            periods_assigned = len(teacher_slots)
            max_capacity = teacher.max_periods_per_week or 24
            workload_pct = int((periods_assigned / max_capacity) * 100) if max_capacity > 0 else 0
            
            # Get assigned batches
            assigned_batches = set(s.batch_id for s in teacher_slots if s.batch_id)
            
            # Get subject names
            subject_names = [Subject.query.get(sid).name for sid in teacher.subject_ids if Subject.query.get(sid)]
            
            teacher_analytics.append({
                "teacherId": teacher.id,
                "teacherName": teacher.name,
                "subjectName": ", ".join(subject_names) if subject_names else "N/A",
                "totalPeriodsAssigned": periods_assigned,
                "maxPeriodsCapacity": max_capacity,
                "workloadPercentage": workload_pct,
                "assignedBatches": len(assigned_batches),
                "hasSpecialDuties": teacher.has_duties,
            })

        # Calculate batch completion
        total_periods_per_batch = (config.periods_per_day or 6) * (config.working_days or 5)
        batch_completion = []
        for batch in batches:
            batch_slots = [s for s in slots if s.batch_id == batch.id and not s.is_lunch]
            filled = len(batch_slots)
            completion_pct = int((filled / total_periods_per_batch) * 100) if total_periods_per_batch > 0 else 0
            
            # Find missing subjects
            assigned_subject_ids = set(s.subject_id for s in batch_slots if s.subject_id)
            missing_subjects = [s.name for s in subjects if s.id not in assigned_subject_ids]
            
            batch_completion.append({
                "batchId": batch.id,
                "batchName": f"Grade {batch.grade} - {batch.section}",
                "studentCount": batch.student_count,
                "totalSlotsAvailable": total_periods_per_batch,
                "slotsFilled": filled,
                "completionPercentage": completion_pct,
                "missingSubjects": missing_subjects,
            })

        # Calculate subject assignments
        subject_assignments = []
        for subject in subjects:
            subject_slots = [s for s in slots if s.subject_id == subject.id and not s.is_lunch]
            assigned = len(subject_slots)
            required = subject.periods_per_week or 0
            assigned_teachers = len(set(s.teacher_id for s in subject_slots))
            is_fully_assigned = required > 0 and assigned >= required
            
            # Get batches needing this subject
            batches_needing = [b.id for b in batches if subject.id in (b.subject_ids or [])]
            batch_names = [f"Grade {Batch.query.get(b).grade}" for b in batches_needing if Batch.query.get(b)]
            
            subject_assignments.append({
                "subjectId": subject.id,
                "subjectName": subject.name,
                "periodsRequired": required,
                "periodsAssigned": assigned,
                "assignedTeachers": assigned_teachers,
                "isFullyAssigned": is_fully_assigned,
                "batchesNeedingIt": batch_names,
            })

        # Calculate overall metrics
        total_slots = len([s for s in slots if not s.is_lunch])
        assigned_slots = len([s for s in slots if s.teacher_id and not s.is_lunch])
        available_slots = total_periods_per_batch * len(batches)
        occupancy_pct = int((assigned_slots / available_slots) * 100) if available_slots > 0 else 0
        
        avg_workload = int(sum(ta["workloadPercentage"] for ta in teacher_analytics) / len(teacher_analytics)) if teacher_analytics else 0
        avg_completion = int(sum(bc["completionPercentage"] for bc in batch_completion) / len(batch_completion)) if batch_completion else 0

        # Build warnings
        warnings = []
        if occupancy_pct < 60:
            warnings.append("⚠️ Low occupancy rate - many periods unassigned")
        for ta in teacher_analytics:
            if ta["workloadPercentage"] > 90:
                warnings.append(f"🔴 {ta['teacherName']} is overloaded ({ta['workloadPercentage']}%)")
        free_slots = available_slots - assigned_slots
        if free_slots > (available_slots * 0.2):
            warnings.append(f"📊 {free_slots} free slots available - schedule could be optimized")

        analytics = {
            "totalTeachers": len(teachers),
            "totalBatches": len(batches),
            "totalSubjects": len(subjects),
            "totalPeriodsAvailable": available_slots,
            "totalPeriodsAssigned": assigned_slots,
            "occupancyPercentage": occupancy_pct,
            "averageTeacherWorkload": avg_workload,
            "averageBatchCompletion": avg_completion,
            "teacherAnalytics": teacher_analytics,
            "batchCompletion": batch_completion,
            "subjectAssignments": subject_assignments,
            "freeSlots": free_slots,
            "conflictCount": 0,  # TODO: Implement conflict detection
            "warnings": warnings,
        }

        return jsonify(analytics), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - School Configuration
# ============================================================================

@api.route("/admin/school-config", methods=["GET"])
@role_required("admin", "principal")
def get_school_config():
    """Get the caller organization's school configuration"""
    config = SchoolConfig.query.filter_by(organization_id=current_org_id()).first() or SchoolConfig()
    return jsonify(config.to_dict()), 200


@api.route("/admin/school-config", methods=["POST"])
@role_required("admin")
def update_school_config():
    """Update school configuration"""
    try:
        data = request.get_json() or {}

        # Validate before persisting so we never store a config that later
        # crashes the scheduler (bad time strings, zero period_duration, etc.).
        from datetime import time as _time

        def _valid_time(v):
            try:
                _time.fromisoformat(str(v))
                return True
            except (ValueError, TypeError):
                return False

        errors = []
        for field in ("start_time", "end_time", "lunch_start", "lunch_end"):
            if field in data and not _valid_time(data[field]):
                errors.append(f"{field} must be a valid HH:MM time")
        for field in ("period_duration", "periods_per_day", "working_days"):
            if field in data:
                val = data[field]
                if not isinstance(val, int) or val <= 0:
                    errors.append(f"{field} must be a positive integer")
        if "working_days" in data and isinstance(data["working_days"], int) and data["working_days"] > 7:
            errors.append("working_days cannot exceed 7")
        if errors:
            return jsonify({"error": "Invalid configuration", "details": errors}), 400

        org_id = current_org_id()
        config = SchoolConfig.query.filter_by(organization_id=org_id).first()
        if not config:
            config = SchoolConfig(organization_id=org_id)
        
        if "start_time" in data: config.start_time = data["start_time"]
        if "end_time" in data: config.end_time = data["end_time"]
        if "lunch_start" in data: config.lunch_start = data["lunch_start"]
        if "lunch_end" in data: config.lunch_end = data["lunch_end"]
        if "period_duration" in data: config.period_duration = data["period_duration"]
        if "periods_per_day" in data: config.periods_per_day = data["periods_per_day"]
        if "working_days" in data: config.working_days = data["working_days"]
        
        config.updated_at = datetime.utcnow()
        db.session.add(config)
        db.session.commit()
        return jsonify(config.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Teacher Management
# ============================================================================

@api.route("/admin/teachers", methods=["GET"])
@role_required("admin", "principal")
def get_teachers():
    """List all teachers in the caller's organization"""
    teachers = Teacher.query.filter_by(organization_id=current_org_id()).all()
    return jsonify([t.to_dict() for t in teachers]), 200


@api.route("/admin/teachers", methods=["POST"])
@role_required("admin")
def create_teacher():
    """Create a new teacher"""
    try:
        data = request.get_json() or {}
        org_id = current_org_id()
        
        # Validate required fields
        if not data.get("name") or not data.get("email"):
            return jsonify({"error": "Name and email are required"}), 400

        email = data.get("email")
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "A user with this email already exists"}), 409

        # Use the provided password, or fall back to a sane default the admin
        # can communicate to the teacher. Either way it is *hashed*, never the
        # old literal "hashed_password_here" placeholder.
        raw_password = data.get("password") or "changeme123"

        # Create user first
        user = User(
            name=data.get("name"),
            email=email,
            role="teacher",
            organization_id=org_id,
            password_hash=generate_password_hash(raw_password),
        )
        db.session.add(user)
        db.session.commit()
        
        # Create teacher record
        teacher = Teacher(
            organization_id=org_id,
            user_id=user.id,
            name=data.get("name"),
            email=data.get("email"),
            subject_ids=data.get("subject_ids", []),
            assigned_batch_ids=data.get("assigned_batch_ids", []),
            is_class_teacher=data.get("is_class_teacher", False),
            class_teacher_batch_id=data.get("class_teacher_batch_id"),
            has_duties=data.get("has_duties", False),
            max_periods_per_week=data.get("max_periods_per_week", 24),
        )
        db.session.add(teacher)
        db.session.commit()
        return jsonify(teacher.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()  # Print to backend logs
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teachers/<int:teacher_id>", methods=["GET"])
@role_required("admin", "principal")
def get_teacher(teacher_id):
    """Get a specific teacher"""
    teacher = owned_or_404(Teacher, teacher_id)
    return jsonify(teacher.to_dict()), 200


@api.route("/admin/teachers/<int:teacher_id>", methods=["PUT"])
@role_required("admin")
def update_teacher(teacher_id):
    """Update a teacher"""
    try:
        teacher = owned_or_404(Teacher, teacher_id)
        data = request.get_json() or {}
        
        if "name" in data: teacher.name = data["name"]
        if "subject_ids" in data: teacher.subject_ids = data["subject_ids"]
        if "assigned_batch_ids" in data: teacher.assigned_batch_ids = data["assigned_batch_ids"]
        if "is_class_teacher" in data: teacher.is_class_teacher = data["is_class_teacher"]
        if "class_teacher_batch_id" in data: teacher.class_teacher_batch_id = data["class_teacher_batch_id"]
        if "has_duties" in data: teacher.has_duties = data["has_duties"]
        if "max_periods_per_week" in data: teacher.max_periods_per_week = data["max_periods_per_week"]
        
        teacher.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(teacher.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teachers/<int:teacher_id>", methods=["DELETE"])
@role_required("admin")
def delete_teacher(teacher_id):
    """Delete a teacher"""
    try:
        teacher = owned_or_404(Teacher, teacher_id)
        user = User.query.get(teacher.user_id)
        
        db.session.delete(teacher)
        if user:
            db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "Teacher deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================

@api.route("/students", methods=["GET"])
@token_required
def get_students():
    """
    Get students by class and section
    Query params:
    - class: class grade (e.g., "7", "12 Science")
    - section: section (e.g., "A", "B")
    """
    try:
        class_grade = request.args.get('class')
        section = request.args.get('section')
        
        if not class_grade or not section:
            return jsonify({"error": "class and section parameters required"}), 400
        
        # Import Student model
        from models import Student
        
        # Query students by class and section, scoped to the caller's org
        students = Student.query.filter_by(
            organization_id=current_org_id(),
            class_grade=class_grade,
            section=section
        ).all()
        
        return jsonify([{
            'id': s.id,
            'student_id': s.student_id,
            'admission_no': s.admission_no,
            'first_name': s.first_name,
            'last_name': s.last_name,
            'gender': s.gender,
            'date_of_birth': s.date_of_birth.isoformat() if s.date_of_birth else None,
            'class_grade': s.class_grade,
            'section': s.section,
            'roll_no': s.roll_no,
            'house_name': s.house_name if hasattr(s, 'house_name') else 'Not Assigned',
            'contact_number': s.contact_number,
            'status': s.status
        } for s in students]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# ADMIN ENDPOINTS - Batch Management
# ============================================================================

@api.route("/admin/batches", methods=["GET"])
@role_required("admin", "principal")
def get_batches():
    """List all batches in the caller's organization"""
    batches = Batch.query.filter_by(organization_id=current_org_id()).all()
    return jsonify([b.to_dict() for b in batches]), 200


@api.route("/admin/batches", methods=["POST"])
@role_required("admin")
def create_batch():
    """Create a new batch"""
    try:
        data = request.get_json() or {}
        batch = Batch(
            organization_id=current_org_id(),
            grade=data.get("grade"),
            section=data.get("section"),
            student_count=data.get("student_count", 0),
            subject_ids=data.get("subject_ids", []),
        )
        db.session.add(batch)
        db.session.commit()
        return jsonify(batch.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/batches/<int:batch_id>", methods=["GET"])
@role_required("admin", "principal")
def get_batch(batch_id):
    """Get a specific batch"""
    batch = owned_or_404(Batch, batch_id)
    return jsonify(batch.to_dict()), 200


@api.route("/admin/batches/<int:batch_id>", methods=["PUT"])
@role_required("admin")
def update_batch(batch_id):
    """Update a batch"""
    try:
        batch = owned_or_404(Batch, batch_id)
        data = request.get_json() or {}
        
        if "grade" in data: batch.grade = data["grade"]
        if "section" in data: batch.section = data["section"]
        if "student_count" in data: batch.student_count = data["student_count"]
        if "subject_ids" in data: batch.subject_ids = data["subject_ids"]
        
        batch.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(batch.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/batches/<int:batch_id>", methods=["DELETE"])
@role_required("admin")
def delete_batch(batch_id):
    """Delete a batch"""
    try:
        batch = owned_or_404(Batch, batch_id)
        db.session.delete(batch)
        db.session.commit()
        return jsonify({"message": "Batch deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Subject Management
# ============================================================================

@api.route("/admin/subjects", methods=["GET"])
@role_required("admin", "principal")
def get_subjects():
    """List all subjects in the caller's organization"""
    subjects = Subject.query.filter_by(organization_id=current_org_id()).all()
    return jsonify([s.to_dict() for s in subjects]), 200


@api.route("/admin/subjects", methods=["POST"])
@role_required("admin")
def create_subject():
    """Create a new subject"""
    try:
        data = request.get_json() or {}
        subject = Subject(
            organization_id=current_org_id(),
            name=data.get("name"),
            periods_per_week=data.get("periods_per_week"),
            batch_ids=data.get("batch_ids", []),
        )
        db.session.add(subject)
        db.session.commit()
        return jsonify(subject.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/subjects/<int:subject_id>", methods=["GET"])
@role_required("admin", "principal")
def get_subject(subject_id):
    """Get a specific subject"""
    subject = owned_or_404(Subject, subject_id)
    return jsonify(subject.to_dict()), 200


@api.route("/admin/subjects/<int:subject_id>", methods=["PUT"])
@role_required("admin")
def update_subject(subject_id):
    """Update a subject"""
    try:
        subject = owned_or_404(Subject, subject_id)
        data = request.get_json() or {}
        
        if "name" in data: subject.name = data["name"]
        if "periods_per_week" in data: subject.periods_per_week = data["periods_per_week"]
        if "batch_ids" in data: subject.batch_ids = data["batch_ids"]
        
        subject.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(subject.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/subjects/<int:subject_id>", methods=["DELETE"])
@role_required("admin")
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        subject = owned_or_404(Subject, subject_id)
        db.session.delete(subject)
        db.session.commit()
        return jsonify({"message": "Subject deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TIMETABLE ENDPOINTS
# ============================================================================

# NOTE: The real POST /api/timetable/generate handler lives in
# timetable_routes.py (blueprint `timetable_bp`). It runs the actual
# SchedulingEngine. A stub used to be defined here with the same URL, which
# shadowed the real one — it has been removed so the engine route is used.


@api.route("/timetable", methods=["GET"])
@role_required("admin", "principal", "teacher", "student")
def get_timetables():
    """List timetables in the caller's organization"""
    timetables = (
        Timetable.query.filter_by(organization_id=current_org_id())
        .order_by(Timetable.generated_at.desc())
        .all()
    )
    return jsonify([t.to_dict() for t in timetables]), 200


@api.route("/timetable/<int:timetable_id>", methods=["GET"])
@role_required("admin", "principal", "teacher", "student")
def get_timetable(timetable_id):
    """Get a specific timetable with all slots"""
    timetable = owned_or_404(Timetable, timetable_id)
    return jsonify(timetable.to_dict(include_slots=True)), 200


@api.route("/timetable/<int:timetable_id>/publish", methods=["POST"])
@role_required("admin")
def publish_timetable(timetable_id):
    """Publish a timetable"""
    try:
        timetable = owned_or_404(Timetable, timetable_id)
        timetable.status = "published"
        timetable.published_at = datetime.utcnow()
        db.session.commit()
        return jsonify(timetable.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TEACHER ENDPOINTS
# ============================================================================

@api.route("/teacher/my-timetable", methods=["GET"])
@role_required("teacher")
def get_teacher_timetable():
    """Get the current user's timetable (teacher view)"""
    # TODO: Extract teacher_id from JWT token
    teacher_id = request.args.get("teacher_id")
    timetable_id = request.args.get("timetable_id")
    
    if not teacher_id or not timetable_id:
        return jsonify({"error": "teacher_id and timetable_id required"}), 400
    
    teacher = owned_or_404(Teacher, teacher_id)
    timetable = owned_or_404(Timetable, timetable_id)
    
    # Get slots for this teacher
    slots = TimetableSlot.query.filter_by(
        timetable_id=timetable.id,
        teacher_id=teacher.id
    ).all()
    
    return jsonify({
        "teacher": teacher.to_dict(),
        "timetable": timetable.to_dict(),
        "slots": [s.to_dict() for s in slots],
        "total_periods": len(slots),
    }), 200


# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================

@api.route("/student/my-timetable", methods=["GET"])
@role_required("student")
def get_student_timetable():
    """Get the current user's batch timetable (student view)"""
    # TODO: Extract batch_id from JWT token (or user's batch_id)
    batch_id = request.args.get("batch_id")
    timetable_id = request.args.get("timetable_id")
    
    if not batch_id or not timetable_id:
        return jsonify({"error": "batch_id and timetable_id required"}), 400
    
    batch = owned_or_404(Batch, batch_id)
    timetable = owned_or_404(Timetable, timetable_id)
    
    # Get slots for this batch
    slots = TimetableSlot.query.filter_by(
        timetable_id=timetable.id,
        batch_id=batch.id
    ).all()
    
    return jsonify({
        "batch": batch.to_dict(),
        "timetable": timetable.to_dict(),
        "slots": [s.to_dict() for s in slots],
    }), 200


# ============================================================================
# PRINCIPAL ENDPOINTS
# ============================================================================

@api.route("/principal/dashboard", methods=["GET"])
@role_required("principal")
def get_principal_dashboard():
    """Get principal dashboard data"""
    timetable_id = request.args.get("timetable_id")
    
    try:
        org_id = current_org_id()
        teachers = Teacher.query.filter_by(organization_id=org_id).all()
        batches = Batch.query.filter_by(organization_id=org_id).all()
        
        teacher_workload = {}
        for teacher in teachers:
            if timetable_id:
                slots = TimetableSlot.query.filter_by(
                    timetable_id=timetable_id,
                    teacher_id=teacher.id
                ).count()
                teacher_workload[teacher.id] = {
                    "name": teacher.name,
                    "periods": slots,
                    "max_periods": teacher.max_periods_per_week,
                    "has_duties": teacher.has_duties,
                    "assigned_batches": [Batch.query.get(bid).to_dict() for bid in teacher.assigned_batch_ids if Batch.query.get(bid)],
                }
            else:
                teacher_workload[teacher.id] = {
                    "name": teacher.name,
                    "max_periods": teacher.max_periods_per_week,
                    "has_duties": teacher.has_duties,
                }
        
        dash_tt = (
            Timetable.query.filter_by(id=timetable_id, organization_id=org_id).first()
            if timetable_id else None
        )
        return jsonify({
            "teachers": [t.to_dict() for t in teachers],
            "batches": [b.to_dict() for b in batches],
            "teacher_workload": teacher_workload,
            "timetable": dash_tt.to_dict() if dash_tt else None,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@api.route("/stats", methods=["GET"])
def get_stats():
    """Get database statistics"""
    return jsonify(get_db_stats()), 200


@api.route("/seed", methods=["POST"])
def seed_data():
    """
    Trigger database seeding (for development only)
    NOTE: This will drop all data and recreate sample data
    """
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "seed.py"],
            cwd="/Users/aarohi_sharma/cpp project/backend",
            capture_output=True,
            text=True,
            timeout=30
        )
        return jsonify({
            "message": "Database seeded successfully",
            "output": result.stdout,
            "stats": get_db_stats(),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PDF EXPORT ENDPOINTS
# ============================================================================

@api.route("/export/timetable/batch/<int:timetable_id>", methods=["GET"])
@token_required
@role_required(["admin", "principal"])
def export_batch_timetable(timetable_id):
    """Export timetable as PDF (batch-wise layout)"""
    try:
        from pdf_utils import export_batch_timetable
        
        timetable = Timetable.query.filter_by(id=timetable_id, organization_id=current_org_id()).first()
        if not timetable:
            return jsonify({"error": "Timetable not found"}), 404
        
        pdf_buffer = export_batch_timetable(timetable_id, school_name=timetable.school_name or "School")
        
        return pdf_buffer.getvalue(), 200, {
            "Content-Disposition": f'attachment; filename="timetable_batch_{timetable_id}.pdf"',
            "Content-Type": "application/pdf"
        }
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/export/timetable/teacher/<int:timetable_id>", methods=["GET"])
@token_required
@role_required(["admin", "principal", "teacher"])
def export_teacher_timetable(timetable_id):
    """Export timetable as PDF (teacher-wise layout)"""
    try:
        from pdf_utils import export_teacher_timetable
        
        timetable = Timetable.query.filter_by(id=timetable_id, organization_id=current_org_id()).first()
        if not timetable:
            return jsonify({"error": "Timetable not found"}), 404
        
        pdf_buffer = export_teacher_timetable(timetable_id, school_name=timetable.school_name or "School")
        
        return pdf_buffer.getvalue(), 200, {
            "Content-Disposition": f'attachment; filename="timetable_teacher_{timetable_id}.pdf"',
            "Content-Type": "application/pdf"
        }
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# LEAVE MANAGEMENT ENDPOINTS
# ============================================================================

@api.route("/leaves/request", methods=["POST"])
@token_required
@role_required(["teacher"])
def request_leave():
    """Teacher requests leave"""
    try:
        from leave_service import LeaveService
        from models import LeaveRequest
        
        data = request.get_json()
        user_id = request.user.get("user_id")
        
        # Get teacher for this user
        user = User.query.get(user_id)
        teacher = Teacher.query.filter_by(user_id=user_id).first()
        
        if not teacher:
            return jsonify({"error": "Teacher profile not found"}), 404
        
        leave_date = datetime.fromisoformat(data.get("leave_date")).date() if isinstance(data.get("leave_date"), str) else data.get("leave_date")
        reason = data.get("reason", "")
        leave_type = data.get("leave_type", "casual")
        
        result = LeaveService.request_leave(teacher.id, leave_date, reason, leave_type)
        
        if result["success"]:
            leave_request = LeaveRequest.query.get(result["leave_request_id"])
            return jsonify(leave_request.to_dict()), 201
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/leaves", methods=["GET"])
@token_required
def get_leaves():
    """Get leave requests (with optional filters)"""
    try:
        from leave_service import LeaveService
        
        user_id = request.user.get("user_id")
        user = User.query.get(user_id)
        
        filters = {"organization_id": current_org_id()}
        
        # Students only see their own teacher's leaves
        if user.role == "teacher":
            teacher = Teacher.query.filter_by(user_id=user_id).first()
            if teacher:
                filters["teacher_id"] = teacher.id
        
        # Apply query parameters
        if request.args.get("status"):
            filters["status"] = request.args.get("status")
        if request.args.get("from_date"):
            filters["from_date"] = request.args.get("from_date")
        if request.args.get("to_date"):
            filters["to_date"] = request.args.get("to_date")
        
        leave_requests = LeaveService.get_leave_requests(filters)
        return jsonify([lr.to_dict() for lr in leave_requests]), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/leaves/<int:leave_request_id>", methods=["GET"])
@token_required
def get_leave(leave_request_id):
    """Get a specific leave request"""
    try:
        from models import LeaveRequest
        
        leave_request = LeaveRequest.query.get(leave_request_id)
        if not leave_request:
            return jsonify({"error": "Leave request not found"}), 404
        
        return jsonify(leave_request.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/leaves/<int:leave_request_id>/approve", methods=["POST"])
@token_required
@role_required(["admin", "principal"])
def approve_leave(leave_request_id):
    """Approve a leave request"""
    try:
        from leave_service import LeaveService
        
        data = request.get_json()
        approved_by_id = request.user.get("user_id")
        substitute_teacher_id = data.get("substitute_teacher_id")
        auto_adjust = data.get("auto_adjust", True)
        
        result = LeaveService.approve_leave(leave_request_id, approved_by_id, substitute_teacher_id, auto_adjust)
        
        if result["success"]:
            return jsonify(result["leave_request"]), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/leaves/<int:leave_request_id>/reject", methods=["POST"])
@token_required
@role_required(["admin", "principal"])
def reject_leave(leave_request_id):
    """Reject a leave request"""
    try:
        from leave_service import LeaveService
        
        data = request.get_json()
        rejection_reason = data.get("rejection_reason", "")
        
        result = LeaveService.reject_leave(leave_request_id, rejection_reason)
        
        if result["success"]:
            return jsonify(result["leave_request"]), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/teachers/<int:teacher_id>/mark-absent", methods=["POST"])
@token_required
@role_required(["admin", "principal"])
def mark_teacher_absent(teacher_id):
    """Mark a teacher as absent for a specific date"""
    try:
        from leave_service import LeaveService
        
        data = request.get_json()
        absent_date = datetime.fromisoformat(data.get("date")).date() if isinstance(data.get("date"), str) else data.get("date")
        
        result = LeaveService.mark_teacher_absent(teacher_id, absent_date)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/leaves/<int:leave_request_id>/substitute-options", methods=["GET"])
@token_required
@role_required(["admin", "principal"])
def get_substitute_options(leave_request_id):
    """Get available substitutes for a leave request"""
    try:
        from models import LeaveRequest, Teacher, Subject
        from leave_service import LeaveService
        
        leave_request = LeaveRequest.query.get(leave_request_id)
        if not leave_request:
            return jsonify({"error": "Leave request not found"}), 404
        
        teacher = Teacher.query.get(leave_request.teacher_id)
        if not teacher:
            return jsonify({"error": "Teacher not found"}), 404
        
        # Find teachers who can substitute
        available_substitutes = []
        
        for subject_id in (teacher.subject_ids or []):
            potential_subs = Teacher.query.all()
            for sub in potential_subs:
                if sub.id != teacher.id and LeaveService._is_substitute_available(sub.id, leave_request.leave_date):
                    available_substitutes.append({
                        "id": sub.id,
                        "name": sub.name,
                        "subjects": [Subject.query.get(s).name for s in sub.subject_ids if Subject.query.get(s)],
                        "load": len([1 for _ in sub.assigned_batch_ids or []])
                    })
        
        # Remove duplicates
        seen_ids = set()
        unique_subs = []
        for sub in available_substitutes:
            if sub["id"] not in seen_ids:
                seen_ids.add(sub["id"])
                unique_subs.append(sub)
        
        return jsonify(unique_subs), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@api.route("/notifications", methods=["GET"])
@token_required
def get_notifications():
    """Get user notifications"""
    try:
        from models import Notification
        
        user_id = request.user.get("user_id")
        limit = request.args.get("limit", 20, type=int)
        unread_only = request.args.get("unread_only", False, type=lambda x: x.lower() == 'true')
        
        query = Notification.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        return jsonify([n.to_dict() for n in notifications]), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/notifications/unread-count", methods=["GET"])
@token_required
def get_unread_notification_count():
    """Get count of unread notifications"""
    try:
        from models import Notification
        
        user_id = request.user.get("user_id")
        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        
        return jsonify({"unread_count": unread_count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/notifications/<int:notification_id>/mark-read", methods=["POST"])
@token_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        from models import Notification
        
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({"error": "Notification not found"}), 404
        
        if notification.user_id != request.user.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify(notification.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/notifications/mark-all-read", methods=["POST"])
@token_required
def mark_all_notifications_read():
    """Mark all user notifications as read"""
    try:
        from models import Notification
        
        user_id = request.user.get("user_id")
        Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
        db.session.commit()
        
        return jsonify({"message": "All notifications marked as read"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/notifications/<int:notification_id>", methods=["DELETE"])
@token_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        from models import Notification
        
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({"error": "Notification not found"}), 404
        
        if notification.user_id != request.user.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({"message": "Notification deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
