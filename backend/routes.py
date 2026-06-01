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

from flask import Blueprint, request, jsonify, abort, make_response
from models import db, User, Batch, Subject, Teacher, SchoolConfig, Timetable, TimetableSlot, LeaveRequest, Notification, Organization, PinnedSlot, TeacherPreference, Charge, Student, Classroom, Stream, SubjectCombination, TeachingGroup, GroupMembership, ClassSubjectConfig
from datetime import datetime, timedelta, date
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
    ACCESS_COOKIE_NAME,
    ORG_COOKIE_NAME,
    TOKEN_EXPIRY_HOURS,
    ORG_TOKEN_EXPIRY_DAYS,
)
from extensions import limiter
from student_service import (
    next_student_code,
    next_admission_no,
    choose_section,
    resequence_rolls,
    fill_missing_rolls,
    section_strengths,
    sections_for_grade,
    student_code_allocator,
    admission_no_allocator,
    section_capacities,
    DEFAULT_SECTION_CAPACITY,
    DEFAULT_ADMISSION_BUFFER,
)
import bulk_import
import os
import re

api = Blueprint("api", __name__, url_prefix="/api")


def _set_auth_cookie(resp, name, token, max_age):
    """Attach an httpOnly auth cookie to a response.

    - httponly  -> JavaScript can't read it, which is the whole point (kills the
      localStorage XSS token-theft vector).
    - samesite=Lax -> the browser won't attach it to cross-site requests, so it
      doubles as CSRF protection for our same-origin SPA + API.
    - secure tied to request.is_secure -> sent only over HTTPS in production,
      while still working over http://localhost in development.
    """
    resp.set_cookie(
        name,
        token,
        max_age=max_age,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
        path="/",
    )


def _clear_auth_cookie(resp, name):
    """Expire an auth cookie (must match path/samesite used when setting)."""
    resp.delete_cookie(name, path="/", samesite="Lax")


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

def get_db_stats(org_id=None):
    """Helper to get database statistics, optionally scoped to one org."""
    def _count(model):
        q = model.query
        if org_id is not None:
            q = q.filter_by(organization_id=org_id)
        return q.count()

    return {
        "users": _count(User),
        "batches": _count(Batch),
        "subjects": _count(Subject),
        "teachers": _count(Teacher),
        "timetables": _count(Timetable),
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
@limiter.limit("10 per minute")
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
        # The token now lives in an httpOnly cookie instead of the JSON body so
        # it never touches JavaScript/localStorage. Only non-sensitive org info
        # is returned for the UI to display.
        resp = make_response(jsonify({"organization": org.to_dict()}), 200)
        _set_auth_cookie(resp, ORG_COOKIE_NAME, token, ORG_TOKEN_EXPIRY_DAYS * 24 * 3600)
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/organizations/logout", methods=["POST"])
def organization_logout():
    """Clear the organization session cookie (and the user cookie with it)."""
    resp = make_response(jsonify({"message": "Organization logged out"}), 200)
    _clear_auth_cookie(resp, ORG_COOKIE_NAME)
    _clear_auth_cookie(resp, ACCESS_COOKIE_NAME)
    return resp


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
@limiter.limit("10 per minute")
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

        # Token goes into an httpOnly cookie, not the response body. The client
        # learns "who am I" from the user object here and from /auth/me later.
        resp = make_response(jsonify({
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "batch_id": user.batch_id,
                "organization_id": org.id,
            },
            "organization": org.to_dict(),
        }), 200)
        _set_auth_cookie(resp, ACCESS_COOKIE_NAME, token, TOKEN_EXPIRY_HOURS * 3600)
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/auth/logout", methods=["POST"])
def logout():
    """Logout: clear the user auth cookie (org session is left intact)."""
    resp = make_response(jsonify({"message": "Logged out"}), 200)
    _clear_auth_cookie(resp, ACCESS_COOKIE_NAME)
    return resp


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
                additional_info["is_class_teacher"] = bool(teacher.is_class_teacher)
                additional_info["class_teacher_batch_id"] = teacher.class_teacher_batch_id
                # Surface the concrete grade/section so the class teacher's UI can
                # scope itself to exactly the class they own.
                if teacher.class_teacher_batch_id:
                    b = Batch.query.get(teacher.class_teacher_batch_id)
                    if b:
                        additional_info["class_teacher_grade"] = b.grade
                        additional_info["class_teacher_section"] = b.section
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
        # periods_per_day is no longer accepted from the client — it is derived
        # from the school hours so the timetable always matches the stated day.
        for field in ("period_duration", "working_days"):
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
        if "working_days" in data: config.working_days = data["working_days"]
        if "has_lunch_break" in data: config.has_lunch_break = bool(data["has_lunch_break"])

        if "pre_primary_mode" in data:
            mode = str(data["pre_primary_mode"] or "").strip().lower()
            if mode not in ("single", "specialist"):
                return jsonify({"error": "pre_primary_mode must be 'single' or 'specialist'"}), 400
            config.pre_primary_mode = mode
        if "pre_primary_support_subjects" in data:
            raw = data["pre_primary_support_subjects"]
            if not isinstance(raw, list):
                return jsonify({"error": "pre_primary_support_subjects must be a list"}), 400
            config.pre_primary_support_subjects = [str(s).strip() for s in raw if str(s).strip()]

        if "default_room_capacity" in data:
            cap = _parse_int(data["default_room_capacity"])
            if not cap or cap <= 0:
                return jsonify({"error": "default_room_capacity must be a positive integer"}), 400
            config.default_room_capacity = cap
        if "ground_max_concurrent_batches" in data:
            gm = _parse_int(data["ground_max_concurrent_batches"])
            if gm is None or gm < 1:
                return jsonify({"error": "ground_max_concurrent_batches must be at least 1"}), 400
            config.ground_max_concurrent_batches = gm

        # ---- Streams / electives / group-formation settings --------------
        if "available_streams" in data:
            raw = data["available_streams"]
            if not isinstance(raw, list):
                return jsonify({"error": "available_streams must be a list"}), 400
            config.available_streams = [str(s).strip() for s in raw if str(s).strip()]
        if "stream_max_strength" in data:
            raw = data["stream_max_strength"] or {}
            if not isinstance(raw, dict):
                return jsonify({"error": "stream_max_strength must be an object"}), 400
            config.stream_max_strength = {str(k): _parse_int(v) for k, v in raw.items() if _parse_int(v)}
        if "min_group_size" in data:
            config.min_group_size = _parse_int(data["min_group_size"]) or config.min_group_size
        if "max_group_size" in data:
            config.max_group_size = _parse_int(data["max_group_size"]) or config.max_group_size
        if "elective_merge_threshold" in data:
            config.elective_merge_threshold = _parse_int(data["elective_merge_threshold"]) or config.elective_merge_threshold
        if "language_start_grade" in data:
            config.language_start_grade = str(data["language_start_grade"]).strip() or config.language_start_grade
        if "allow_group_override" in data:
            config.allow_group_override = bool(data["allow_group_override"])

        # ---- Generation mode / zero period / assembly / class-teacher-first --
        if "generation_mode" in data:
            gm = str(data["generation_mode"]).strip().lower()
            if gm not in ("global", "class_first"):
                return jsonify({"error": "generation_mode must be 'global' or 'class_first'"}), 400
            config.generation_mode = gm
        if "class_teacher_first_period" in data:
            config.class_teacher_first_period = bool(data["class_teacher_first_period"])

        if "zero_period_enabled" in data:
            config.zero_period_enabled = bool(data["zero_period_enabled"])
        if "zero_period_start" in data:
            config.zero_period_start = str(data["zero_period_start"]).strip() or config.zero_period_start
        if "zero_period_duration" in data:
            config.zero_period_duration = _parse_int(data["zero_period_duration"]) or config.zero_period_duration
        if "zero_period_in_hours" in data:
            config.zero_period_in_hours = bool(data["zero_period_in_hours"])
        if "zero_period_in_workload" in data:
            config.zero_period_in_workload = bool(data["zero_period_in_workload"])
        if "zero_period_grades" in data:
            raw = data["zero_period_grades"] or []
            if not isinstance(raw, list):
                return jsonify({"error": "zero_period_grades must be a list"}), 400
            config.zero_period_grades = [str(g).strip() for g in raw if str(g).strip()]

        if "assembly_mode" in data:
            am = str(data["assembly_mode"]).strip().lower()
            if am not in ("disabled", "daily", "day_wise", "grade_wise"):
                return jsonify({"error": "assembly_mode invalid"}), 400
            config.assembly_mode = am
        if "assembly_duration" in data:
            config.assembly_duration = _parse_int(data["assembly_duration"]) or config.assembly_duration
        if "assembly_period" in data:
            config.assembly_period = _parse_int(data["assembly_period"]) or config.assembly_period
        if "assembly_grades" in data:
            raw = data["assembly_grades"] or []
            if not isinstance(raw, list):
                return jsonify({"error": "assembly_grades must be a list"}), 400
            config.assembly_grades = [str(g).strip() for g in raw if str(g).strip()]
        if "assembly_schedule" in data:
            raw = data["assembly_schedule"] or {}
            if not isinstance(raw, dict):
                return jsonify({"error": "assembly_schedule must be an object"}), 400
            config.assembly_schedule = {str(k): [str(g).strip() for g in (v or [])]
                                        for k, v in raw.items()}

        if "has_short_break" in data:
            config.has_short_break = bool(data["has_short_break"])
        if "short_break_start" in data:
            config.short_break_start = str(data["short_break_start"]).strip() or config.short_break_start
        if "short_break_end" in data:
            config.short_break_end = str(data["short_break_end"]).strip() or config.short_break_end

        workload_changed = False
        if "target_contact_periods_per_week" in data:
            try:
                tgt = int(data["target_contact_periods_per_week"])
                if tgt > 0:
                    config.target_contact_periods_per_week = tgt
                    workload_changed = True
            except (TypeError, ValueError):
                return jsonify({"error": "target_contact_periods_per_week must be a positive integer"}), 400
        if "class_teacher_hours_per_week" in data:
            try:
                cth = int(data["class_teacher_hours_per_week"])
                if cth < 0:
                    raise ValueError
                config.class_teacher_hours_per_week = cth
                workload_changed = True
            except (TypeError, ValueError):
                return jsonify({"error": "class_teacher_hours_per_week must be a non-negative integer"}), 400

        # Validate the window actually yields at least one period.
        from period_utils import school_periods_per_day
        if school_periods_per_day(config) < 1:
            return jsonify({"error": "End time must be after start time by at least one period"}), 400
        # Keep the stored period count in sync with the school hours.
        config.periods_per_day = school_periods_per_day(config)

        config.updated_at = datetime.utcnow()
        db.session.add(config)

        # If any workload setting changed, rebalance every teacher's teaching
        # capacity (target - charge hours - class-teacher hours) so totals stay equal.
        if workload_changed:
            tgt = config.target_contact_periods_per_week
            cth = (config.class_teacher_hours_per_week
                   if config.class_teacher_hours_per_week is not None else DEFAULT_CLASS_TEACHER_HOURS)
            for t in Teacher.query.filter_by(organization_id=org_id).all():
                _recompute_teacher_capacity(t, tgt, cth)

        db.session.commit()
        return jsonify(config.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Teacher Management
# ============================================================================

DEFAULT_TARGET_CONTACT = 40


def _org_target_contact(org_id):
    """The org's common weekly contact target (teaching + charge hours)."""
    cfg = SchoolConfig.query.filter_by(organization_id=org_id).first()
    if cfg and cfg.target_contact_periods_per_week:
        return cfg.target_contact_periods_per_week
    return DEFAULT_TARGET_CONTACT


DEFAULT_CLASS_TEACHER_HOURS = 5


def _class_teacher_hours(org_id):
    """Extra hours for class teachers for this org (defaults to 5, editable)."""
    cfg = SchoolConfig.query.filter_by(organization_id=org_id).first()
    if not cfg or cfg.class_teacher_hours_per_week is None:
        return DEFAULT_CLASS_TEACHER_HOURS
    return cfg.class_teacher_hours_per_week


def _recompute_teacher_capacity(teacher, target, ct_hours):
    """Teaching cap = target - manual charge hours - class-teacher hours (if any)."""
    reserved = (teacher.charge_hours or 0)
    if teacher.is_class_teacher:
        reserved += ct_hours
    teacher.max_periods_per_week = max(0, target - reserved)


def _apply_teaching_and_charges(teacher, data, org_id):
    """Normalize teaching_assignments + charges, derive flat lists, and set the
    teacher's dynamic teaching capacity (target - charge hours)."""
    if "teaching_assignments" in data:
        assignments = []
        for entry in (data.get("teaching_assignments") or []):
            try:
                sid = int(entry.get("subject_id"))
            except (TypeError, ValueError, AttributeError):
                continue
            bids = []
            for b in (entry.get("batch_ids") or []):
                try:
                    bids.append(int(b))
                except (TypeError, ValueError):
                    continue
            assignments.append({"subject_id": sid, "batch_ids": sorted(set(bids))})
        teacher.teaching_assignments = assignments
        # Keep the flat lists in sync (scheduler fallback + other consumers).
        teacher.subject_ids = sorted({a["subject_id"] for a in assignments})
        teacher.assigned_batch_ids = sorted({b for a in assignments for b in a["batch_ids"]})
    else:
        if "subject_ids" in data:
            teacher.subject_ids = data["subject_ids"]
        if "assigned_batch_ids" in data:
            teacher.assigned_batch_ids = data["assigned_batch_ids"]

    # Grade-level capability (subject + grades) used by the fair auto-distributor.
    if "subject_grades" in data:
        caps = []
        for entry in (data.get("subject_grades") or []):
            try:
                sid = int(entry.get("subject_id"))
            except (TypeError, ValueError, AttributeError):
                continue
            grades = [str(g) for g in (entry.get("grades") or [])]
            caps.append({"subject_id": sid, "grades": grades})
        teacher.subject_grades = caps

    if "charges" in data:
        charges = []
        for c in (data.get("charges") or []):
            try:
                hours = int(c.get("hours_per_week") or 0)
            except (TypeError, ValueError, AttributeError):
                hours = 0
            charges.append({
                "charge_id": c.get("charge_id"),
                "name": c.get("name") or "Charge",
                "hours_per_week": max(0, hours),
            })
        teacher.charges = charges

    # Members of a non-teaching department (Library/Fees) are substitute-only.
    dept_takes = {c.id: c.takes_classes for c in Charge.query.filter_by(organization_id=org_id).all()}
    teacher.takes_classes = not any(
        dept_takes.get(c.get("charge_id")) is False for c in (teacher.charges or [])
    )

    # Dynamic weekly teaching capacity so total contact load stays balanced.
    # Class-teacher hours come from the coordinator-entered config, never assumed.
    _recompute_teacher_capacity(teacher, _org_target_contact(org_id), _class_teacher_hours(org_id))


@api.route("/admin/teachers", methods=["GET"])
@role_required("admin", "principal")
def get_teachers():
    """List all teachers in the caller's organization"""
    teachers = Teacher.query.filter_by(organization_id=current_org_id()).all()
    return jsonify([t.to_dict() for t in teachers]), 200


@api.route("/admin/teachers", methods=["POST"])
@role_required("admin", "principal")
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
            unavailable_slots=data.get("unavailable_slots", []),
            is_class_teacher=data.get("is_class_teacher", False),
            class_teacher_batch_id=data.get("class_teacher_batch_id"),
            has_duties=data.get("has_duties", False),
            phone=(data.get("phone") or None),
            gender=(data.get("gender") or None),
            qualification=(data.get("qualification") or None),
            designation=(data.get("designation") or None),
            joining_date=_parse_date(data.get("joining_date")),
            primary_subject=(data.get("primary_subject") or None),
            secondary_subject=(data.get("secondary_subject") or None),
            experience_years=_parse_int(data.get("experience_years")),
            availability=(data.get("availability") or None),
            status=(data.get("status") or "active"),
        )
        # Subjects→classes, charges, and dynamic teaching capacity.
        _apply_teaching_and_charges(teacher, data, org_id)
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
@role_required("admin", "principal")
def update_teacher(teacher_id):
    """Update a teacher"""
    try:
        teacher = owned_or_404(Teacher, teacher_id)
        data = request.get_json() or {}
        user = User.query.get(teacher.user_id)

        if "name" in data:
            teacher.name = data["name"]
            if user:
                user.name = data["name"]
        if "email" in data and data["email"] and data["email"] != teacher.email:
            # Email is the login id, so it must stay unique across all users.
            clash = User.query.filter(User.email == data["email"], User.id != teacher.user_id).first()
            if clash:
                return jsonify({"error": "A user with this email already exists"}), 409
            teacher.email = data["email"]
            if user:
                user.email = data["email"]
        if "unavailable_slots" in data: teacher.unavailable_slots = data["unavailable_slots"]
        if "is_class_teacher" in data: teacher.is_class_teacher = data["is_class_teacher"]
        if "class_teacher_batch_id" in data: teacher.class_teacher_batch_id = data["class_teacher_batch_id"]
        if "has_duties" in data: teacher.has_duties = data["has_duties"]
        if "phone" in data: teacher.phone = data["phone"] or None
        if "gender" in data: teacher.gender = data["gender"] or None
        if "qualification" in data: teacher.qualification = data["qualification"] or None
        if "designation" in data: teacher.designation = data["designation"] or None
        if "joining_date" in data: teacher.joining_date = _parse_date(data["joining_date"])
        if "primary_subject" in data: teacher.primary_subject = data["primary_subject"] or None
        if "secondary_subject" in data: teacher.secondary_subject = data["secondary_subject"] or None
        if "experience_years" in data: teacher.experience_years = _parse_int(data["experience_years"])
        if "availability" in data: teacher.availability = data["availability"] or None
        if "status" in data: teacher.status = data["status"] or "active"

        # Subjects→classes, charges, and dynamic teaching capacity. This also
        # keeps subject_ids/assigned_batch_ids in sync and recomputes the cap.
        _apply_teaching_and_charges(teacher, data, current_org_id())

        teacher.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(teacher.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teachers/<int:teacher_id>", methods=["DELETE"])
@role_required("admin", "principal")
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
# TEACHER PREFERENCE ENDPOINTS (soft scheduling constraints + workload targets)
# ============================================================================

def _default_preference_payload(teacher_id):
    """Empty-but-valid preference object used when a teacher has none saved yet."""
    return {
        "teacher_id": teacher_id,
        "preferred_classes": [],
        "preferred_subjects": [],
        "preferred_slots": [],
        "blocked_slots": [],
        "max_periods_day": None,
        "max_periods_week": None,
        "allow_class_teacher_charge": True,
        "allow_extra_charge": True,
    }


@api.route("/admin/teachers/<int:teacher_id>/preferences", methods=["GET"])
@role_required("admin", "principal")
def get_teacher_preferences(teacher_id):
    """Return a teacher's soft preferences (defaults if none have been set)."""
    teacher = owned_or_404(Teacher, teacher_id)
    pref = TeacherPreference.query.filter_by(
        teacher_id=teacher.id, organization_id=current_org_id()
    ).first()
    if not pref:
        return jsonify(_default_preference_payload(teacher.id)), 200
    return jsonify(pref.to_dict()), 200


@api.route("/admin/teachers/<int:teacher_id>/preferences", methods=["PUT"])
@role_required("admin")
def upsert_teacher_preferences(teacher_id):
    """Create or update a teacher's soft preferences / workload targets."""
    try:
        teacher = owned_or_404(Teacher, teacher_id)
        org_id = current_org_id()
        data = request.get_json() or {}

        pref = TeacherPreference.query.filter_by(
            teacher_id=teacher.id, organization_id=org_id
        ).first()
        if not pref:
            pref = TeacherPreference(organization_id=org_id, teacher_id=teacher.id)
            db.session.add(pref)

        def _int_or_none(v):
            try:
                return int(v) if v not in (None, "") else None
            except (TypeError, ValueError):
                return None

        if "preferred_classes" in data:
            pref.preferred_classes = [int(x) for x in (data["preferred_classes"] or [])]
        if "preferred_subjects" in data:
            pref.preferred_subjects = [int(x) for x in (data["preferred_subjects"] or [])]
        if "preferred_slots" in data:
            pref.preferred_slots = data["preferred_slots"] or []
        if "blocked_slots" in data:
            pref.blocked_slots = data["blocked_slots"] or []
        if "max_periods_day" in data:
            pref.max_periods_day = _int_or_none(data["max_periods_day"])
        if "max_periods_week" in data:
            pref.max_periods_week = _int_or_none(data["max_periods_week"])
        if "allow_class_teacher_charge" in data:
            pref.allow_class_teacher_charge = bool(data["allow_class_teacher_charge"])
        if "allow_extra_charge" in data:
            pref.allow_extra_charge = bool(data["allow_extra_charge"])

        pref.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(pref.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CHARGE CATALOG ENDPOINTS (non-teaching duties teachers can be assigned)
# ============================================================================

def _assigned_member_counts(org_id):
    """How many teachers are currently assigned to each charge/department id."""
    counts = {}
    for t in Teacher.query.filter_by(organization_id=org_id).all():
        for c in (t.charges or []):
            cid = c.get("charge_id")
            if cid is not None:
                counts[cid] = counts.get(cid, 0) + 1
    return counts


@api.route("/admin/charges", methods=["GET"])
@role_required("admin", "principal")
def list_charges():
    """List the org's departments/charges with assigned-vs-required coverage."""
    org_id = current_org_id()
    charges = Charge.query.filter_by(organization_id=org_id).order_by(Charge.name).all()
    counts = _assigned_member_counts(org_id)
    # Class teachership is tracked via the is_class_teacher flag, not a charge,
    # so reflect that count for a department literally named "Class Teacher".
    class_teacher_count = Teacher.query.filter_by(
        organization_id=org_id, is_class_teacher=True
    ).count()
    out = []
    for c in charges:
        d = c.to_dict()
        if c.name.strip().lower() == "class teacher":
            d["assigned_members"] = class_teacher_count
        else:
            d["assigned_members"] = counts.get(c.id, 0)
        out.append(d)
    return jsonify(out), 200


@api.route("/admin/charges", methods=["POST"])
@role_required("admin")
def create_charge():
    """Add a department/charge: { name, default_hours_per_week, members_required, takes_classes }."""
    try:
        data = request.get_json() or {}
        org_id = current_org_id()
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Charge name is required"}), 400
        if Charge.query.filter_by(organization_id=org_id, name=name).first():
            return jsonify({"error": "A charge with this name already exists"}), 409

        def _int(v, default):
            try:
                return max(0, int(v))
            except (TypeError, ValueError):
                return default

        charge = Charge(
            organization_id=org_id,
            name=name,
            default_hours_per_week=_int(data.get("default_hours_per_week"), 2),
            members_required=_int(data.get("members_required"), 1),
            takes_classes=bool(data.get("takes_classes", True)),
        )
        db.session.add(charge)
        db.session.commit()
        return jsonify(charge.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/charges/<int:charge_id>", methods=["PUT"])
@role_required("admin")
def update_charge(charge_id):
    """Edit a department/charge (name, hours, members required, takes-classes)."""
    try:
        charge = owned_or_404(Charge, charge_id)
        data = request.get_json() or {}
        if "name" in data and (data["name"] or "").strip():
            charge.name = data["name"].strip()
        if "default_hours_per_week" in data:
            try:
                charge.default_hours_per_week = max(0, int(data["default_hours_per_week"]))
            except (TypeError, ValueError):
                pass
        if "members_required" in data:
            try:
                charge.members_required = max(0, int(data["members_required"]))
            except (TypeError, ValueError):
                pass
        if "takes_classes" in data:
            charge.takes_classes = bool(data["takes_classes"])
        db.session.commit()
        return jsonify(charge.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/charges/<int:charge_id>", methods=["DELETE"])
@role_required("admin")
def delete_charge(charge_id):
    """Delete a charge type from the catalog (existing teacher assignments keep their snapshot)."""
    try:
        charge = owned_or_404(Charge, charge_id)
        db.session.delete(charge)
        db.session.commit()
        return jsonify({"message": "Charge deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# FAIR AUTO-ASSIGNMENT + WORKLOAD SUMMARY
# ============================================================================

@api.route("/admin/teachers/auto-assign-sections", methods=["POST"])
@role_required("admin")
def auto_assign_sections():
    """Distribute concrete sections across teachers from their grade-level
    capability (subject + grades), balancing load and guaranteeing coverage.

    For every (class, subject) the class needs, the least-loaded capable teacher
    who *takes classes* is chosen. Non-teaching staff (Library/Fees) are skipped
    and left as the substitute pool. The result is written to teaching_assignments
    (and is fully editable afterward)."""
    try:
        from collections import defaultdict
        org_id = current_org_id()
        batches = Batch.query.filter_by(organization_id=org_id).all()
        subjects = {s.id: s for s in Subject.query.filter_by(organization_id=org_id).all()}
        teachers = Teacher.query.filter_by(organization_id=org_id).all()

        capable = defaultdict(list)   # (subject_id, grade) -> [teacher]
        load = {t.id: 0 for t in teachers}     # projected weekly periods
        sections = {t.id: 0 for t in teachers}
        work = {t.id: defaultdict(set) for t in teachers}  # subject_id -> {batch_ids}
        for t in teachers:
            if not t.takes_classes:
                continue
            for cap in (t.subject_grades or []):
                sid = cap.get("subject_id")
                for g in (cap.get("grades") or []):
                    capable[(sid, str(g))].append(t)

        uncovered = []
        assigned_count = 0
        over_capacity = 0
        for b in batches:
            for sid in (b.subject_ids or []):
                subj = subjects.get(sid)
                periods = subj.periods_per_week if subj else 1
                pool = capable.get((sid, str(b.grade)), [])
                if not pool:
                    uncovered.append({
                        "grade": b.grade, "section": b.section,
                        "subject_id": sid, "subject": subj.name if subj else f"#{sid}",
                    })
                    continue
                under = [t for t in pool if load[t.id] + periods <= (t.max_periods_per_week or 0)]
                chooser = under if under else pool
                if not under:
                    over_capacity += 1
                chooser.sort(key=lambda t: (load[t.id], sections[t.id]))
                chosen = chooser[0]
                work[chosen.id][sid].add(b.id)
                load[chosen.id] += periods
                sections[chosen.id] += 1
                assigned_count += 1

        for t in teachers:
            assignments = [{"subject_id": sid, "batch_ids": sorted(bids)}
                           for sid, bids in work[t.id].items() if bids]
            t.teaching_assignments = assignments
            t.subject_ids = sorted({a["subject_id"] for a in assignments})
            t.assigned_batch_ids = sorted({bid for a in assignments for bid in a["batch_ids"]})
        db.session.commit()

        return jsonify({
            "assigned": assigned_count,
            "over_capacity_assignments": over_capacity,
            "uncovered": uncovered,
            "teacher_loads": sorted(
                [{"teacher_id": t.id, "name": t.name, "periods": load[t.id],
                  "sections": sections[t.id], "capacity": t.max_periods_per_week}
                 for t in teachers if t.takes_classes],
                key=lambda x: -x["periods"],
            ),
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/workload/summary", methods=["GET"])
@role_required("admin", "principal")
def workload_summary():
    """Stats that drive the suggested per-teacher contact target."""
    import math
    org_id = current_org_id()
    batches = Batch.query.filter_by(organization_id=org_id).all()
    subjects = {s.id: s for s in Subject.query.filter_by(organization_id=org_id).all()}
    teachers = Teacher.query.filter_by(organization_id=org_id).all()
    try:
        total_students = Student.query.filter_by(organization_id=org_id).count()
    except Exception:
        total_students = None

    total_demand = 0
    for b in batches:
        for sid in (b.subject_ids or []):
            s = subjects.get(sid)
            total_demand += (s.periods_per_week if s else 0)

    teaching_teachers = sum(1 for t in teachers if t.takes_classes)
    substitute_teachers = sum(1 for t in teachers if not t.takes_classes)
    suggested = math.ceil(total_demand / teaching_teachers) if teaching_teachers else 0
    cfg = SchoolConfig.query.filter_by(organization_id=org_id).first()

    return jsonify({
        "total_students": total_students,
        "total_classes": len(batches),
        "total_subjects": len(subjects),
        "total_weekly_periods_demanded": total_demand,
        "teaching_teachers": teaching_teachers,
        "substitute_teachers": substitute_teachers,
        "suggested_target_periods_per_week": suggested,
        "current_target": cfg.target_contact_periods_per_week if cfg else None,
        "periods_per_day": cfg.periods_per_day if cfg else None,
        "working_days": cfg.working_days if cfg else None,
    }), 200


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
# STUDENT MANAGEMENT (admin + principal + scoped class teacher)
# ============================================================================
#
# Permission model:
#   * admin / principal -> full access to every student in their organization
#   * class teacher      -> manage ONLY students of the class+section they own
# Transfers (moving a student between sections) are admin/principal only, since
# a class teacher should not move a pupil out of their own scope.

def _acting_teacher():
    """Teacher row for the currently authenticated user (None if not a teacher)."""
    user = getattr(request, "user", None)
    if not user or user.get("role") != "teacher":
        return None
    return Teacher.query.filter_by(
        user_id=user.get("user_id"), organization_id=current_org_id()
    ).first()


def _class_teacher_scope():
    """(grade, section) the acting class teacher owns, else None."""
    t = _acting_teacher()
    if not t or not t.is_class_teacher or not t.class_teacher_batch_id:
        return None
    b = Batch.query.filter_by(
        id=t.class_teacher_batch_id, organization_id=current_org_id()
    ).first()
    return (str(b.grade), b.section) if b else None


def _is_admin_or_principal():
    return (getattr(request, "user", {}) or {}).get("role") in ("admin", "principal")


def _can_manage_scope(class_grade, section):
    """May the caller manage students in this grade/section?"""
    if _is_admin_or_principal():
        return True
    scope = _class_teacher_scope()
    return bool(scope) and (str(class_grade), section) == scope


def _split_name(data):
    """Resolve first/last name from either explicit fields or a single full_name."""
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    if not first and data.get("full_name"):
        parts = str(data["full_name"]).strip().split()
        first = parts[0] if parts else ""
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first, last


def _parse_date(value):
    """Parse an ISO date string (YYYY-MM-DD) into a date, tolerating None/blank."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_int(value):
    """Parse an int, tolerating None/blank/garbage (returns None instead of raising)."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


@api.route("/admin/students", methods=["GET"])
@role_required("admin", "principal", "teacher")
def list_students():
    """List students, filtered by class/section/status/search.

    Class teachers are automatically restricted to their own class+section.
    """
    org_id = current_org_id()
    scope = None if _is_admin_or_principal() else _class_teacher_scope()
    if not _is_admin_or_principal() and not scope:
        return jsonify({"error": "You are not assigned as a class teacher"}), 403

    q = Student.query.filter_by(organization_id=org_id)

    class_grade = request.args.get("class_grade") or request.args.get("class")
    section = request.args.get("section")
    status = request.args.get("status")
    search = (request.args.get("q") or "").strip().lower()

    if scope:
        class_grade, section = scope[0], scope[1]
    if class_grade:
        q = q.filter(Student.class_grade == str(class_grade))
    if section:
        q = q.filter(Student.section == section)
    if status:
        q = q.filter(Student.status == status)

    students = q.all()
    if search:
        students = [
            s for s in students
            if search in f"{s.first_name} {s.last_name}".lower()
            or search in (s.student_id or "").lower()
            or search in (s.admission_no or "").lower()
        ]
    students.sort(key=lambda s: (s.roll_no if s.roll_no is not None else 9999,
                                 (s.first_name or "").lower()))
    return jsonify([s.to_dict() for s in students]), 200


@api.route("/admin/students/sections", methods=["GET"])
@role_required("admin", "principal", "teacher")
def student_section_strengths():
    """Section strengths for a grade (drives the balancing UI)."""
    org_id = current_org_id()
    class_grade = request.args.get("class_grade") or request.args.get("class")
    if not class_grade:
        return jsonify({"error": "class_grade is required"}), 400
    strengths = section_strengths(org_id, class_grade)
    caps, default = section_capacities(org_id, class_grade)
    return jsonify({
        "class_grade": str(class_grade),
        "sections": sections_for_grade(org_id, class_grade),
        "strengths": strengths,
        # Per-section capacity (from the batch override / home room / org default).
        "capacities": caps,
        # Org-wide default for any section without its own capacity.
        "capacity": default,
        "buffer": DEFAULT_ADMISSION_BUFFER,
    }), 200


@api.route("/admin/students", methods=["POST"])
@role_required("admin", "principal", "teacher")
def create_student():
    """Add a student. Auto-generates roll & admission numbers and (optionally)
    auto-places the student into the lowest-strength section of the class."""
    try:
        org_id = current_org_id()
        data = request.get_json() or {}

        first, last = _split_name(data)
        if not first:
            return jsonify({"error": "Student name is required"}), 400
        class_grade = str(data.get("class_grade") or "").strip()
        if not class_grade:
            return jsonify({"error": "Class is required"}), 400

        # Section: explicit, the class teacher's own, or auto-balanced.
        section = (data.get("section") or "").strip()
        over_capacity = False
        ct_scope = _class_teacher_scope()
        if ct_scope:
            # Class teachers may only add into their own class+section.
            if class_grade != ct_scope[0]:
                return jsonify({"error": "You can only add students to your own class"}), 403
            section = ct_scope[1]
        elif not section:
            section, over_capacity = choose_section(
                org_id, class_grade,
                capacity=_parse_int(data.get("capacity")),
                buffer=int(data.get("buffer") or DEFAULT_ADMISSION_BUFFER),
            )

        if not _can_manage_scope(class_grade, section):
            return jsonify({"error": "Not allowed to manage this class/section"}), 403

        # Respect an explicitly provided admission number (org's own pattern);
        # otherwise auto-generate continuing the org's existing format.
        provided_adm = (data.get("admission_number") or data.get("admission_no") or "").strip()
        if provided_adm and Student.query.filter_by(admission_no=provided_adm).first():
            return jsonify({"error": f"Admission number '{provided_adm}' already exists"}), 409

        # Respect an explicitly provided roll number; otherwise auto-resequence.
        provided_roll = data.get("roll_no")
        explicit_roll = str(provided_roll).strip() not in ("", "None") if provided_roll is not None else False

        student = Student(
            organization_id=org_id,
            student_id=next_student_code(),
            admission_no=provided_adm or next_admission_no(org_id),
            first_name=first,
            last_name=last,
            email=(data.get("email") or data.get("parent_email") or None),
            father_name=(data.get("father_name") or None),
            mother_name=(data.get("mother_name") or None),
            contact_number=(data.get("phone") or data.get("contact_number") or None),
            gender=(data.get("gender") or None),
            date_of_birth=_parse_date(data.get("date_of_birth")),
            address=(data.get("address") or None),
            blood_group=(data.get("blood_group") or None),
            class_grade=class_grade,
            section=section,
            admission_date=_parse_date(data.get("joining_date") or data.get("admission_date")) or date.today(),
            status=(data.get("status") or "Active"),
            stream=(data.get("stream") or None),
            subject_combination=(data.get("subject_combination") or None),
            elective_subjects=(data.get("elective_subjects") if isinstance(data.get("elective_subjects"), list) else []),
        )
        if explicit_roll:
            try:
                student.roll_no = int(provided_roll)
            except (TypeError, ValueError):
                explicit_roll = False
        db.session.add(student)
        db.session.flush()  # assign id before any roll work
        # Keep org-supplied numbers intact; only auto-number when none was given.
        if explicit_roll:
            fill_missing_rolls(org_id, class_grade, section)
        else:
            resequence_rolls(org_id, class_grade, section)
        db.session.commit()

        result = student.to_dict()
        result["auto_section"] = not (data.get("section") or ct_scope)
        result["over_capacity"] = over_capacity
        return jsonify(result), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/students/<int:student_id>", methods=["PUT"])
@role_required("admin", "principal", "teacher")
def update_student(student_id):
    """Edit a student. Name/status/section changes trigger roll re-sequencing.

    A section or class change here behaves like a transfer (both old and new
    sections are renumbered); class teachers can't move a student out of scope.
    """
    try:
        org_id = current_org_id()
        student = owned_or_404(Student, student_id)
        if not _can_manage_scope(student.class_grade, student.section):
            return jsonify({"error": "Not allowed to manage this student"}), 403

        data = request.get_json() or {}
        old_grade, old_section = student.class_grade, student.section

        if "first_name" in data or "last_name" in data or "full_name" in data:
            first, last = _split_name({
                "first_name": data.get("first_name", student.first_name),
                "last_name": data.get("last_name", student.last_name),
                "full_name": data.get("full_name"),
            })
            if first:
                student.first_name = first
                student.last_name = last
        if "email" in data or "parent_email" in data:
            student.email = (data.get("email") or data.get("parent_email")) or None
        if "father_name" in data: student.father_name = data["father_name"] or None
        if "mother_name" in data: student.mother_name = data["mother_name"] or None
        if "phone" in data: student.contact_number = data["phone"] or None
        if "contact_number" in data: student.contact_number = data["contact_number"] or None
        if "gender" in data: student.gender = data["gender"] or None
        if "date_of_birth" in data: student.date_of_birth = _parse_date(data["date_of_birth"])
        if "address" in data: student.address = data["address"] or None
        if "blood_group" in data: student.blood_group = data["blood_group"] or None
        if "roll_no" in data and str(data["roll_no"]).strip() not in ("", "None"):
            try:
                student.roll_no = int(data["roll_no"])
            except (TypeError, ValueError):
                pass
        if "admission_number" in data or "admission_no" in data:
            new_adm = (data.get("admission_number") or data.get("admission_no") or "").strip()
            if new_adm and new_adm != student.admission_no:
                clash = Student.query.filter(Student.admission_no == new_adm, Student.id != student.id).first()
                if clash:
                    return jsonify({"error": f"Admission number '{new_adm}' already exists"}), 409
                student.admission_no = new_adm
        if "joining_date" in data or "admission_date" in data:
            student.admission_date = _parse_date(data.get("joining_date") or data.get("admission_date")) or student.admission_date
        if "status" in data: student.status = data["status"] or "Active"
        if "stream" in data: student.stream = data["stream"] or None
        if "subject_combination" in data: student.subject_combination = data["subject_combination"] or None
        if "elective_subjects" in data:
            student.elective_subjects = data["elective_subjects"] if isinstance(data["elective_subjects"], list) else []

        # Section / class moves (admin & principal only).
        new_grade = str(data.get("class_grade", student.class_grade))
        new_section = data.get("section", student.section)
        if (new_grade, new_section) != (old_grade, old_section):
            if not _is_admin_or_principal():
                return jsonify({"error": "Only admin/principal can move a student between sections"}), 403
            if not _can_manage_scope(new_grade, new_section):
                return jsonify({"error": "Not allowed to manage the destination class/section"}), 403
            student.class_grade = new_grade
            student.section = new_section

        student.updated_at = datetime.utcnow()
        db.session.flush()
        # Renumber affected sections (old + new) so rolls stay alphabetical/contiguous.
        resequence_rolls(org_id, old_grade, old_section)
        if (student.class_grade, student.section) != (old_grade, old_section):
            resequence_rolls(org_id, student.class_grade, student.section)
        db.session.commit()
        return jsonify(student.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/students/<int:student_id>", methods=["DELETE"])
@role_required("admin", "principal", "teacher")
def delete_student(student_id):
    """Delete a student and renumber the rolls of their old section."""
    try:
        org_id = current_org_id()
        student = owned_or_404(Student, student_id)
        if not _can_manage_scope(student.class_grade, student.section):
            return jsonify({"error": "Not allowed to manage this student"}), 403
        grade, section = student.class_grade, student.section
        db.session.delete(student)
        db.session.flush()
        resequence_rolls(org_id, grade, section)
        db.session.commit()
        return jsonify({"message": "Student deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/students/<int:student_id>/transfer", methods=["POST"])
@role_required("admin", "principal")
def transfer_student(student_id):
    """Move a student to a different section (and optionally grade).

    Renumbers both the source and destination sections. Admin/principal only.
    """
    try:
        org_id = current_org_id()
        student = owned_or_404(Student, student_id)
        data = request.get_json() or {}
        dest_section = (data.get("section") or "").strip()
        dest_grade = str(data.get("class_grade") or student.class_grade)
        if not dest_section:
            return jsonify({"error": "Destination section is required"}), 400

        old_grade, old_section = student.class_grade, student.section
        if (dest_grade, dest_section) == (old_grade, old_section):
            return jsonify({"error": "Student is already in that section"}), 400

        student.class_grade = dest_grade
        student.section = dest_section
        student.updated_at = datetime.utcnow()
        db.session.flush()
        resequence_rolls(org_id, old_grade, old_section)
        resequence_rolls(org_id, dest_grade, dest_section)
        db.session.commit()
        return jsonify(student.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/students/resequence-rolls", methods=["POST"])
@role_required("admin", "principal", "teacher")
def resequence_section_rolls():
    """Force a fresh alphabetical roll numbering for one section."""
    try:
        org_id = current_org_id()
        data = request.get_json() or {}
        class_grade = str(data.get("class_grade") or "")
        section = (data.get("section") or "").strip()
        if not class_grade or not section:
            return jsonify({"error": "class_grade and section are required"}), 400
        if not _can_manage_scope(class_grade, section):
            return jsonify({"error": "Not allowed to manage this class/section"}), 403
        count = resequence_rolls(org_id, class_grade, section)
        db.session.commit()
        return jsonify({"message": f"Renumbered {count} students", "count": count}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# BULK IMPORT (CSV / XLSX) — students & teachers
# ============================================================================
#
# Two-step flow so the admin always previews before anything is written:
#   1. POST .../import/<entity>/preview  (multipart file) -> mapped + validated
#      rows, with per-row status (ok / warning / duplicate / invalid). No writes.
#   2. POST .../import/<entity>/commit   (JSON rows + skip_invalid) -> bulk create
#      and an error report (success_count / failure_count / errors).

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Optional fields whose emptiness is surfaced as a (non-blocking) warning.
_STUDENT_OPTIONAL = [
    "parent_name", "mother_name", "email", "phone", "section", "admission_number",
    "roll_no", "date_of_birth", "gender", "address", "blood_group", "admission_date",
]
_TEACHER_OPTIONAL = ["phone", "qualification", "designation"]


def _row_status(issues):
    levels = {i["level"] for i in issues}
    if "invalid" in levels:
        return "invalid"
    if "duplicate" in levels:
        return "duplicate"
    return "ok"


def _annotate_students(org_id, records, scope):
    """Validate parsed student rows against the org; return annotated rows + counts."""
    existing = Student.query.filter_by(organization_id=org_id).all()
    db_adm = {(s.admission_no or "").lower() for s in existing if s.admission_no}
    db_namekey = {
        (f"{s.first_name} {s.last_name}".strip().lower(), str(s.class_grade), s.section)
        for s in existing
    }
    seen_adm, seen_name = set(), set()
    rows = []
    for rec in records:
        data = dict(rec["data"])
        issues = []
        name = (data.get("name") or "").strip()
        klass = (data.get("class") or "").strip()
        section = (data.get("section") or "").strip()
        email = (data.get("email") or "").strip()
        adm = (data.get("admission_number") or "").strip()

        if scope:
            if klass and str(klass) != scope[0]:
                issues.append({"level": "invalid", "msg": f"Not your class (you manage {scope[0]})"})
            klass = scope[0]
            section = scope[1]
            data["class"], data["section"] = klass, section

        if not name:
            issues.append({"level": "invalid", "msg": "Missing name"})
        if not klass:
            issues.append({"level": "invalid", "msg": "Missing class"})
        if email and not EMAIL_RE.match(email):
            issues.append({"level": "invalid", "msg": "Invalid email format"})

        namekey = (name.lower(), str(klass), section)
        if adm:
            al = adm.lower()
            if al in db_adm:
                issues.append({"level": "duplicate", "msg": f"Admission no '{adm}' already exists"})
            elif al in seen_adm:
                issues.append({"level": "duplicate", "msg": f"Admission no '{adm}' repeated in file"})
            seen_adm.add(al)
        if name and klass:
            if namekey in db_namekey:
                issues.append({"level": "duplicate", "msg": "A student with this name already exists in that class/section"})
            elif namekey in seen_name:
                issues.append({"level": "duplicate", "msg": "Duplicate name in file for this class/section"})
            seen_name.add(namekey)

        missing = [f for f in _STUDENT_OPTIONAL if not (data.get(f) or "").strip()]
        rows.append({"row": rec["row"], "data": data, "issues": issues,
                     "missing": missing, "status": _row_status(issues)})
    return rows


def _annotate_teachers(org_id, records):
    """Validate parsed teacher rows; emails must be present & unique (login id)."""
    db_email = {u.email.lower() for u in User.query.all() if u.email}
    seen_email = set()
    rows = []
    for rec in records:
        data = dict(rec["data"])
        issues = []
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()

        if not name:
            issues.append({"level": "invalid", "msg": "Missing name"})
        if not email:
            issues.append({"level": "invalid", "msg": "Email is required (used as login id)"})
        elif not EMAIL_RE.match(email):
            issues.append({"level": "invalid", "msg": "Invalid email format"})
        else:
            el = email.lower()
            if el in db_email:
                issues.append({"level": "duplicate", "msg": f"A user with email '{email}' already exists"})
            elif el in seen_email:
                issues.append({"level": "duplicate", "msg": f"Email '{email}' repeated in file"})
            seen_email.add(el)

        missing = [f for f in _TEACHER_OPTIONAL if not (data.get(f) or "").strip()]
        rows.append({"row": rec["row"], "data": data, "issues": issues,
                     "missing": missing, "status": _row_status(issues)})
    return rows


def _counts(rows):
    return {
        "total": len(rows),
        "valid": sum(1 for r in rows if r["status"] == "ok"),
        "duplicates": sum(1 for r in rows if r["status"] == "duplicate"),
        "invalid": sum(1 for r in rows if r["status"] == "invalid"),
    }


@api.route("/admin/import/<entity>/preview", methods=["POST"])
@role_required("admin", "principal", "teacher")
def import_preview(entity):
    """Parse an uploaded CSV/XLSX, fuzzy-match headers, validate — no writes."""
    if entity not in ("students", "teachers"):
        return jsonify({"error": "Unknown import type"}), 404
    org_id = current_org_id()

    scope = None
    if not _is_admin_or_principal():
        if entity == "teachers":
            return jsonify({"error": "Only admin/principal can import teachers"}), 403
        scope = _class_teacher_scope()
        if not scope:
            return jsonify({"error": "You are not assigned as a class teacher"}), 403

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        headers, raw_rows = bulk_import.read_table(file.filename, file.read())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Could not read the file. Please check the format."}), 400

    fields = bulk_import.FIELD_SETS[entity]
    mapping = bulk_import.match_columns(headers, fields)
    records = bulk_import.extract_records(raw_rows, mapping)

    if entity == "students":
        rows = _annotate_students(org_id, records, scope)
    else:
        rows = _annotate_teachers(org_id, records)

    return jsonify({
        "entity": entity,
        "fields": list(fields.keys()),
        "mapping": mapping,
        "unmapped_headers": bulk_import.unmapped_headers(headers, mapping),
        "scope": {"class_grade": scope[0], "section": scope[1]} if scope else None,
        "counts": _counts(rows),
        "rows": rows,
    }), 200


@api.route("/admin/import/<entity>/commit", methods=["POST"])
@role_required("admin", "principal", "teacher")
def import_commit(entity):
    """Bulk-create from confirmed rows. Body: { rows:[{data}], skip_invalid:bool }."""
    if entity not in ("students", "teachers"):
        return jsonify({"error": "Unknown import type"}), 404
    org_id = current_org_id()

    scope = None
    if not _is_admin_or_principal():
        if entity == "teachers":
            return jsonify({"error": "Only admin/principal can import teachers"}), 403
        scope = _class_teacher_scope()
        if not scope:
            return jsonify({"error": "You are not assigned as a class teacher"}), 403

    payload = request.get_json() or {}
    in_rows = payload.get("rows") or []
    skip_invalid = bool(payload.get("skip_invalid", True))
    # Re-validate server-side; never trust the client's status flags.
    records = [{"row": r.get("row", i + 2), "data": r.get("data") or {}}
               for i, r in enumerate(in_rows)]

    if entity == "students":
        annotated = _annotate_students(org_id, records, scope)
    else:
        annotated = _annotate_teachers(org_id, records)

    success, errors = 0, []
    touched_sections = set()

    try:
        if entity == "students":
            alloc_code = student_code_allocator()
            alloc_adm = admission_no_allocator(org_id)
            # Track, per section, whether any explicit roll numbers were supplied
            # so we don't clobber an org's own numbering with a resequence.
            manual_sections = set()
            for r in annotated:
                if r["status"] != "ok":
                    if skip_invalid:
                        errors.append({"row": r["row"], "name": r["data"].get("name", ""),
                                       "error": "; ".join(i["msg"] for i in r["issues"])})
                        continue
                    return jsonify({"error": f"Row {r['row']} has problems. Fix it or enable 'skip invalid rows'.",
                                    "row": r["row"]}), 400
                d = r["data"]
                first, last = _split_name({"full_name": d.get("name")})
                klass = scope[0] if scope else str(d.get("class"))
                section = scope[1] if scope else (d.get("section") or "").strip()
                if not section:
                    section, _ = choose_section(org_id, klass)
                student = Student(
                    organization_id=org_id,
                    student_id=alloc_code(),
                    admission_no=(d.get("admission_number") or "").strip() or alloc_adm(),
                    first_name=first, last_name=last,
                    email=(d.get("email") or d.get("parent_email") or None),
                    father_name=(d.get("parent_name") or None),
                    mother_name=(d.get("mother_name") or None),
                    contact_number=(d.get("phone") or None),
                    gender=(d.get("gender") or None),
                    date_of_birth=_parse_date(d.get("date_of_birth")),
                    address=(d.get("address") or None),
                    blood_group=(d.get("blood_group") or None),
                    class_grade=klass, section=section,
                    admission_date=_parse_date(d.get("admission_date")) or date.today(),
                    status="Active",
                )
                roll_in = (d.get("roll_no") or "").strip()
                if roll_in:
                    try:
                        student.roll_no = int(roll_in)
                        manual_sections.add((klass, section))
                    except (TypeError, ValueError):
                        pass
                db.session.add(student)
                touched_sections.add((klass, section))
                success += 1
            db.session.flush()
            for grade, section in touched_sections:
                # Sections with any org-supplied roll keep their numbers (only
                # gaps are filled); fully-auto sections are resequenced A→Z.
                if (grade, section) in manual_sections:
                    fill_missing_rolls(org_id, grade, section)
                else:
                    resequence_rolls(org_id, grade, section)
            db.session.commit()
        else:
            target = _org_target_contact(org_id)
            ct_hours = _class_teacher_hours(org_id)
            for r in annotated:
                if r["status"] != "ok":
                    if skip_invalid:
                        errors.append({"row": r["row"], "name": r["data"].get("name", ""),
                                       "error": "; ".join(i["msg"] for i in r["issues"])})
                        continue
                    return jsonify({"error": f"Row {r['row']} has problems. Fix it or enable 'skip invalid rows'.",
                                    "row": r["row"]}), 400
                d = r["data"]
                user = User(name=d.get("name"), email=d.get("email"), role="teacher",
                            organization_id=org_id,
                            password_hash=generate_password_hash("changeme123"))
                db.session.add(user)
                db.session.flush()
                teacher = Teacher(
                    organization_id=org_id, user_id=user.id,
                    name=d.get("name"), email=d.get("email"),
                    phone=(d.get("phone") or None),
                    gender=(d.get("gender") or None),
                    qualification=(d.get("qualification") or None),
                    designation=(d.get("designation") or None),
                    joining_date=_parse_date(d.get("joining_date")),
                    primary_subject=(d.get("primary_subject") or None),
                    secondary_subject=(d.get("secondary_subject") or None),
                    experience_years=_parse_int(d.get("experience_years")),
                    availability=(d.get("availability") or None),
                    status=(d.get("status") or "active"),
                )
                _apply_teaching_and_charges(teacher, {}, org_id)
                db.session.add(teacher)
                success += 1
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "success_count": 0,
                        "failure_count": len(annotated)}), 500

    return jsonify({
        "success_count": success,
        "failure_count": len(errors),
        "errors": errors,
    }), 200


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
            periods_per_day=data.get("periods_per_day") or None,
            homeroom_teacher_id=data.get("homeroom_teacher_id") or None,
            room_id=data.get("room_id") or None,
            capacity=_parse_int(data.get("capacity")),
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
        if "periods_per_day" in data: batch.periods_per_day = data["periods_per_day"] or None
        if "homeroom_teacher_id" in data: batch.homeroom_teacher_id = data["homeroom_teacher_id"] or None
        if "room_id" in data: batch.room_id = data["room_id"] or None
        if "capacity" in data: batch.capacity = _parse_int(data["capacity"])
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
# ADMIN ENDPOINTS - Rooms / Facilities
# ============================================================================

@api.route("/admin/rooms", methods=["GET"])
@role_required("admin", "principal")
def list_rooms():
    """All rooms for the caller's organization, ordered by floor then code."""
    rooms = (
        Classroom.query.filter_by(organization_id=current_org_id())
        .order_by(Classroom.floor.asc().nullsfirst(), Classroom.room_id.asc())
        .all()
    )
    return jsonify([r.to_dict() for r in rooms]), 200


def _room_capacity_default(org_id):
    cfg = SchoolConfig.query.filter_by(organization_id=org_id).first()
    return (cfg.default_room_capacity if cfg and cfg.default_room_capacity else 50)


@api.route("/admin/rooms", methods=["POST"])
@role_required("admin")
def create_room():
    """Create a room. room_id (code) must be unique within the organization."""
    try:
        from room_utils import ALL_ROOM_TYPES
        data = request.get_json() or {}
        org_id = current_org_id()
        code = (data.get("room_id") or "").strip()
        name = (data.get("room_name") or "").strip()
        if not code or not name:
            return jsonify({"error": "room_id (code) and room_name are required"}), 400
        room_type = (data.get("room_type") or "regular").strip().lower()
        if room_type not in ALL_ROOM_TYPES:
            return jsonify({"error": f"room_type must be one of {ALL_ROOM_TYPES}"}), 400
        if Classroom.query.filter_by(organization_id=org_id, room_id=code).first():
            return jsonify({"error": f"A room with code '{code}' already exists"}), 409
        cap = _parse_int(data.get("capacity")) or _room_capacity_default(org_id)
        room = Classroom(
            organization_id=org_id,
            room_id=code,
            room_name=name,
            capacity=cap,
            room_type=room_type,
            floor=_parse_int(data.get("floor")),
            facilities=data.get("facilities") or [],
        )
        db.session.add(room)
        db.session.commit()
        return jsonify(room.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/rooms/<int:room_id>", methods=["PUT"])
@role_required("admin")
def update_room(room_id):
    """Update a room."""
    try:
        from room_utils import ALL_ROOM_TYPES
        room = owned_or_404(Classroom, room_id)
        data = request.get_json() or {}
        if "room_id" in data and data["room_id"]:
            new_code = data["room_id"].strip()
            clash = Classroom.query.filter(
                Classroom.organization_id == room.organization_id,
                Classroom.room_id == new_code,
                Classroom.id != room.id,
            ).first()
            if clash:
                return jsonify({"error": f"A room with code '{new_code}' already exists"}), 409
            room.room_id = new_code
        if "room_name" in data and data["room_name"]: room.room_name = data["room_name"].strip()
        if "room_type" in data:
            rt = (data["room_type"] or "regular").strip().lower()
            if rt not in ALL_ROOM_TYPES:
                return jsonify({"error": f"room_type must be one of {ALL_ROOM_TYPES}"}), 400
            room.room_type = rt
        if "capacity" in data: room.capacity = _parse_int(data["capacity"]) or room.capacity
        if "floor" in data: room.floor = _parse_int(data["floor"])
        if "facilities" in data: room.facilities = data["facilities"] or []
        db.session.commit()
        return jsonify(room.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/rooms/<int:room_id>", methods=["DELETE"])
@role_required("admin")
def delete_room(room_id):
    """Delete a room (and detach any batch that used it as a home classroom)."""
    try:
        room = owned_or_404(Classroom, room_id)
        Batch.query.filter_by(room_id=room.id).update({"room_id": None})
        db.session.delete(room)
        db.session.commit()
        return jsonify({"message": "Room deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/rooms/auto-generate", methods=["POST"])
@role_required("admin")
def auto_generate_rooms():
    """Generate a default room inventory across floors for the organization.

    Body (optional): { regular_rooms, regular_capacity, floors,
                       special: [{room_type, room_name, capacity}], replace }
    With no body it lays out a sensible default: enough regular classrooms to
    cover every section plus the standard set of special rooms + a ground.
    """
    try:
        from room_service import generate_default_rooms
        data = request.get_json() or {}
        org_id = current_org_id()
        created = generate_default_rooms(org_id, options=data)
        db.session.commit()
        return jsonify({"created": created,
                        "rooms": [r.to_dict() for r in
                                  Classroom.query.filter_by(organization_id=org_id).all()]}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/rooms/setup", methods=["POST"])
@role_required("admin")
def setup_rooms():
    """One-shot capacity setup: add sections to fit students at the configured
    capacity, (re)generate the room inventory across floors, assign each section
    a fixed home room, and redistribute students so none exceeds the limit."""
    try:
        from room_service import setup_capacity
        org_id = current_org_id()
        result = setup_capacity(org_id, options=request.get_json() or {})
        db.session.commit()
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/rooms/exchange", methods=["POST"])
@role_required("admin")
def exchange_rooms():
    """Swap the fixed home classrooms of two sections.

    Body: { "batch_a": <id>, "batch_b": <id> }. Capacity follows the room, so it
    is swapped too. Returns warnings when a section would no longer fit its new
    room's capacity (the swap is still applied — the admin decides)."""
    try:
        from student_service import section_strengths
        data = request.get_json() or {}
        a_id = _parse_int(data.get("batch_a"))
        b_id = _parse_int(data.get("batch_b"))
        if not a_id or not b_id or a_id == b_id:
            return jsonify({"error": "Pick two different sections to exchange"}), 400

        a = owned_or_404(Batch, a_id)
        b = owned_or_404(Batch, b_id)

        ra, rb = a.room_id, b.room_id
        if not ra and not rb:
            return jsonify({"error": "Neither section has a home room to exchange"}), 400

        # Swap the rooms; capacity travels with the room.
        a.room_id, b.room_id = rb, ra
        room_for_a = Classroom.query.get(rb) if rb else None
        room_for_b = Classroom.query.get(ra) if ra else None
        a.capacity = room_for_a.capacity if room_for_a else None
        b.capacity = room_for_b.capacity if room_for_b else None
        if room_for_a:
            room_for_a.assigned_class = f"{a.grade}-{a.section}"
        if room_for_b:
            room_for_b.assigned_class = f"{b.grade}-{b.section}"

        db.session.commit()

        warnings = []
        for batch, room in ((a, room_for_a), (b, room_for_b)):
            if not room:
                continue
            strength = section_strengths(batch.organization_id, batch.grade).get(batch.section, 0)
            if strength > (room.capacity or 0):
                warnings.append(
                    f"{batch.grade}-{batch.section} has {strength} students but "
                    f"{room.room_name} holds {room.capacity}."
                )

        return jsonify({
            "message": "Rooms exchanged",
            "batches": [a.to_dict(), b.to_dict()],
            "warnings": warnings,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/rooms/assign-home", methods=["POST"])
@role_required("admin")
def assign_home_rooms():
    """Give every regular (non-pre-primary handled too) batch a fixed home room
    and set each section's capacity from its room, then redistribute students so
    no section exceeds capacity."""
    try:
        from room_service import assign_home_rooms_to_batches
        org_id = current_org_id()
        result = assign_home_rooms_to_batches(org_id)
        db.session.commit()
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Streams & Subject Combinations (senior school)
# ============================================================================

@api.route("/admin/streams", methods=["GET"])
@role_required("admin", "principal", "teacher")
def list_streams():
    rows = Stream.query.filter_by(organization_id=current_org_id()).order_by(
        Stream.grade.asc(), Stream.name.asc()).all()
    return jsonify([s.to_dict() for s in rows]), 200


@api.route("/admin/streams", methods=["POST"])
@role_required("admin")
def create_stream():
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        grade = str(data.get("grade") or "").strip()
        if not name or not grade:
            return jsonify({"error": "name and grade are required"}), 400
        s = Stream(
            organization_id=current_org_id(), name=name, grade=grade,
            academic_year=(data.get("academic_year") or None),
            max_strength=_parse_int(data.get("max_strength")),
            separate_sections=bool(data.get("separate_sections", True)),
            active=bool(data.get("active", True)),
        )
        db.session.add(s)
        db.session.commit()
        return jsonify(s.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/streams/<int:stream_id>", methods=["PUT"])
@role_required("admin")
def update_stream(stream_id):
    try:
        s = owned_or_404(Stream, stream_id)
        data = request.get_json() or {}
        if "name" in data and data["name"]: s.name = data["name"].strip()
        if "grade" in data and data["grade"]: s.grade = str(data["grade"]).strip()
        if "academic_year" in data: s.academic_year = data["academic_year"] or None
        if "max_strength" in data: s.max_strength = _parse_int(data["max_strength"])
        if "separate_sections" in data: s.separate_sections = bool(data["separate_sections"])
        if "active" in data: s.active = bool(data["active"])
        db.session.commit()
        return jsonify(s.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/streams/<int:stream_id>", methods=["DELETE"])
@role_required("admin")
def delete_stream(stream_id):
    try:
        s = owned_or_404(Stream, stream_id)
        SubjectCombination.query.filter_by(stream_id=s.id).update({"stream_id": None})
        db.session.delete(s)
        db.session.commit()
        return jsonify({"message": "Stream deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/subject-combinations", methods=["GET"])
@role_required("admin", "principal", "teacher")
def list_combinations():
    rows = SubjectCombination.query.filter_by(organization_id=current_org_id()).all()
    return jsonify([c.to_dict() for c in rows]), 200


@api.route("/admin/subject-combinations", methods=["POST"])
@role_required("admin")
def create_combination():
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        c = SubjectCombination(
            organization_id=current_org_id(),
            stream_id=_parse_int(data.get("stream_id")),
            name=name, grade=str(data.get("grade") or "").strip() or None,
            subject_ids=(data.get("subject_ids") if isinstance(data.get("subject_ids"), list) else []),
            active=bool(data.get("active", True)),
        )
        db.session.add(c)
        db.session.commit()
        return jsonify(c.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/subject-combinations/<int:comb_id>", methods=["PUT"])
@role_required("admin")
def update_combination(comb_id):
    try:
        c = owned_or_404(SubjectCombination, comb_id)
        data = request.get_json() or {}
        if "name" in data and data["name"]: c.name = data["name"].strip()
        if "stream_id" in data: c.stream_id = _parse_int(data["stream_id"])
        if "grade" in data: c.grade = str(data["grade"]).strip() or None
        if "subject_ids" in data and isinstance(data["subject_ids"], list): c.subject_ids = data["subject_ids"]
        if "active" in data: c.active = bool(data["active"])
        db.session.commit()
        return jsonify(c.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/subject-combinations/<int:comb_id>", methods=["DELETE"])
@role_required("admin")
def delete_combination(comb_id):
    try:
        c = owned_or_404(SubjectCombination, comb_id)
        db.session.delete(c)
        db.session.commit()
        return jsonify({"message": "Combination deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Teaching Groups (dynamic stream/elective/language groups)
# ============================================================================

@api.route("/admin/teaching-groups", methods=["GET"])
@role_required("admin", "principal", "teacher")
def list_teaching_groups():
    """List teaching groups, optionally filtered by ?grade= or ?group_type=."""
    q = TeachingGroup.query.filter_by(organization_id=current_org_id())
    grade = request.args.get("grade")
    gtype = request.args.get("group_type")
    if grade:
        q = q.filter_by(grade=str(grade))
    if gtype:
        q = q.filter_by(group_type=gtype)
    rows = q.order_by(TeachingGroup.grade.asc(), TeachingGroup.group_type.asc(),
                      TeachingGroup.name.asc()).all()
    return jsonify([g.to_dict() for g in rows]), 200


@api.route("/admin/teaching-groups/generate", methods=["POST"])
@role_required("admin")
def generate_teaching_groups():
    """Rebuild auto teaching groups from current student stream/elective choices.
    Admin-locked groups are preserved."""
    try:
        from group_service import generate_groups
        result = generate_groups(current_org_id(), options=request.get_json() or {})
        db.session.commit()
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teaching-groups/<int:group_id>", methods=["GET"])
@role_required("admin", "principal", "teacher")
def get_teaching_group(group_id):
    g = owned_or_404(TeachingGroup, group_id)
    return jsonify(g.to_dict(include_members=True)), 200


@api.route("/admin/teaching-groups", methods=["POST"])
@role_required("admin")
def create_teaching_group():
    """Manually create a teaching group (admin override)."""
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        grade = str(data.get("grade") or "").strip()
        if not name or not grade:
            return jsonify({"error": "name and grade are required"}), 400
        g = TeachingGroup(
            organization_id=current_org_id(), name=name, grade=grade,
            stream=(data.get("stream") or None), section=(data.get("section") or None),
            group_type=(data.get("group_type") or "elective"),
            subject_id=_parse_int(data.get("subject_id")),
            teacher_id=_parse_int(data.get("teacher_id")),
            room_id=_parse_int(data.get("room_id")),
            periods_per_week=_parse_int(data.get("periods_per_week")),
            block_key=(data.get("block_key") or None),
            locked=bool(data.get("locked", False)),
            auto_generated=False,
        )
        db.session.add(g)
        db.session.commit()
        return jsonify(g.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teaching-groups/<int:group_id>", methods=["PUT"])
@role_required("admin")
def update_teaching_group(group_id):
    """Override a group: assign teacher/room, rename, lock/unlock, set block."""
    try:
        g = owned_or_404(TeachingGroup, group_id)
        data = request.get_json() or {}
        if "name" in data and data["name"]: g.name = data["name"].strip()
        if "teacher_id" in data: g.teacher_id = _parse_int(data["teacher_id"])
        if "room_id" in data: g.room_id = _parse_int(data["room_id"])
        if "periods_per_week" in data: g.periods_per_week = _parse_int(data["periods_per_week"])
        if "block_key" in data: g.block_key = data["block_key"] or None
        if "locked" in data: g.locked = bool(data["locked"])
        if "subject_id" in data: g.subject_id = _parse_int(data["subject_id"])
        db.session.commit()
        return jsonify(g.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teaching-groups/<int:group_id>", methods=["DELETE"])
@role_required("admin")
def delete_teaching_group(group_id):
    try:
        g = owned_or_404(TeachingGroup, group_id)
        db.session.delete(g)
        db.session.commit()
        return jsonify({"message": "Group deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teaching-groups/<int:group_id>/members", methods=["POST"])
@role_required("admin")
def modify_group_members(group_id):
    """Add or remove a student from a group (manual override).
    Body: { "student_id": <id>, "action": "add" | "remove", "from_group_id": <id?> }."""
    try:
        g = owned_or_404(TeachingGroup, group_id)
        data = request.get_json() or {}
        student_id = _parse_int(data.get("student_id"))
        action = (data.get("action") or "add").lower()
        if not student_id:
            return jsonify({"error": "student_id is required"}), 400
        owned_or_404(Student, student_id)  # ownership check

        if action == "remove":
            GroupMembership.query.filter_by(group_id=g.id, student_id=student_id).delete()
        else:
            # Optionally move out of a sibling group first.
            from_id = _parse_int(data.get("from_group_id"))
            if from_id:
                GroupMembership.query.filter_by(group_id=from_id, student_id=student_id).delete()
            exists = GroupMembership.query.filter_by(group_id=g.id, student_id=student_id).first()
            if not exists:
                db.session.add(GroupMembership(
                    organization_id=g.organization_id, group_id=g.id, student_id=student_id))
        db.session.commit()
        return jsonify(g.to_dict(include_members=True)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teaching-groups/validate", methods=["GET"])
@role_required("admin", "principal")
def validate_student_coverage():
    """Student-level no-class-loss check against a generated timetable.

    ?timetable_id= (defaults to latest). For every student verifies their core
    subjects are scheduled, each chosen elective has a slot, and no two of their
    slots overlap. Returns counts + a sample of issues."""
    try:
        from group_validation import validate_coverage
        org_id = current_org_id()
        tid = _parse_int(request.args.get("timetable_id"))
        if not tid:
            latest = Timetable.query.filter_by(organization_id=org_id).order_by(
                Timetable.created_at.desc()).first()
            tid = latest.id if latest else None
        if not tid:
            return jsonify({"error": "No timetable to validate"}), 400
        result = validate_coverage(org_id, tid)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN ENDPOINTS - Class-wise subject configuration
# ============================================================================

@api.route("/admin/class-subject-config", methods=["GET"])
@role_required("admin", "principal")
def get_class_subject_config():
    """Per-class subject config. ?grade= filters to one grade.

    Returns existing rows plus, for the requested grade, the list of subjects
    assigned to that grade's batches so the UI can show every subject (even
    those not yet configured, which fall back to the org-wide Subject default).
    """
    org_id = current_org_id()
    grade = request.args.get("grade")
    q = ClassSubjectConfig.query.filter_by(organization_id=org_id)
    if grade:
        q = q.filter_by(grade=str(grade))
    rows = [c.to_dict() for c in q.all()]

    grades = sorted({str(b.grade) for b in Batch.query.filter_by(organization_id=org_id).all()})
    subjects_for_grade = []
    if grade:
        bids = {b.id for b in Batch.query.filter_by(organization_id=org_id, grade=str(grade)).all()}
        seen = set()
        for s in Subject.query.filter_by(organization_id=org_id).all():
            if set(s.batch_ids or []) & bids and s.id not in seen:
                seen.add(s.id)
                subjects_for_grade.append({
                    "subject_id": s.id, "name": s.name,
                    "periods_per_week": s.periods_per_week,
                    "max_periods_per_day": getattr(s, "max_periods_per_day", 1),
                    "subject_type": getattr(s, "subject_type", "core"),
                })
    return jsonify({"configs": rows, "grades": grades,
                    "subjects_for_grade": subjects_for_grade}), 200


@api.route("/admin/class-subject-config", methods=["POST"])
@role_required("admin")
def save_class_subject_config():
    """Bulk upsert per-class subject config rows.

    Body: {"grade": "6", "items": [{subject_id, periods_per_week, min_periods,
    max_periods, max_per_day, allow_consecutive, allow_daily, priority,
    preferred_spread}, ...]}. Rows are matched on (grade, subject_id)."""
    org_id = current_org_id()
    data = request.get_json() or {}
    grade = str(data.get("grade") or "").strip()
    items = data.get("items")
    if not grade or not isinstance(items, list):
        return jsonify({"error": "grade and items[] are required"}), 400

    saved = 0
    for it in items:
        sid = _parse_int(it.get("subject_id"))
        if not sid:
            continue
        row = ClassSubjectConfig.query.filter_by(
            organization_id=org_id, grade=grade, subject_id=sid).first()
        if not row:
            row = ClassSubjectConfig(organization_id=org_id, grade=grade, subject_id=sid)
            db.session.add(row)
        ppw = _parse_int(it.get("periods_per_week"))
        if ppw is not None:
            row.periods_per_week = max(0, ppw)
        row.min_periods = _parse_int(it.get("min_periods"))
        row.max_periods = _parse_int(it.get("max_periods"))
        mpd = _parse_int(it.get("max_per_day"))
        row.max_per_day = mpd if mpd and mpd > 0 else 1
        row.allow_consecutive = bool(it.get("allow_consecutive", False))
        row.allow_daily = bool(it.get("allow_daily", True))
        pr = str(it.get("priority") or "medium").lower()
        row.priority = pr if pr in ("high", "medium", "low") else "medium"
        row.preferred_spread = str(it.get("preferred_spread") or "even")
        saved += 1
    db.session.commit()
    return jsonify({"saved": saved}), 200


@api.route("/admin/class-subject-config/<int:config_id>", methods=["DELETE"])
@role_required("admin")
def delete_class_subject_config(config_id):
    """Delete one per-class subject config (reverts that subject to defaults)."""
    org_id = current_org_id()
    row = ClassSubjectConfig.query.filter_by(id=config_id, organization_id=org_id).first()
    if not row:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@api.route("/admin/timetable-planning/validate", methods=["GET"])
@role_required("admin", "principal")
def validate_timetable_planning():
    """Class-wise planning checks: subject weekly counts, assembly, zero period,
    teacher double-booking and class-teacher-first. ?timetable_id= (else latest)."""
    try:
        from planning_validation import validate_planning
        org_id = current_org_id()
        tid = _parse_int(request.args.get("timetable_id"))
        if not tid:
            latest = Timetable.query.filter_by(organization_id=org_id).order_by(
                Timetable.created_at.desc()).first()
            tid = latest.id if latest else None
        if not tid:
            return jsonify({"error": "No timetable to validate"}), 400
        return jsonify(validate_planning(org_id, tid)), 200
    except Exception as e:
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
            max_periods_per_day=data.get("max_periods_per_day", 1),
            requires_double=data.get("requires_double", False),
            batch_ids=data.get("batch_ids", []),
            subject_type=(data.get("subject_type") or "core"),
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
        if "max_periods_per_day" in data: subject.max_periods_per_day = data["max_periods_per_day"]
        if "requires_double" in data: subject.requires_double = data["requires_double"]
        if "batch_ids" in data: subject.batch_ids = data["batch_ids"]
        if "subject_type" in data: subject.subject_type = (data["subject_type"] or "core")
        
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
# PINNED / FIXED SLOTS - periods locked by the admin before generation
# ============================================================================

@api.route("/admin/pinned-slots", methods=["GET"])
@role_required("admin", "principal")
def list_pinned_slots():
    """List all pinned/fixed periods for the caller's organization."""
    pins = PinnedSlot.query.filter_by(organization_id=current_org_id()).all()
    return jsonify([p.to_dict() for p in pins]), 200


@api.route("/admin/pinned-slots", methods=["POST"])
@role_required("admin")
def create_pinned_slot():
    """Lock a period: { batch_id, subject_id, day, period_number, teacher_id? }."""
    try:
        data = request.get_json() or {}
        org_id = current_org_id()

        required = ("batch_id", "subject_id", "day", "period_number")
        if any(data.get(f) in (None, "") for f in required):
            return jsonify({"error": "batch_id, subject_id, day and period_number are required"}), 400

        # Everything referenced must belong to this organization.
        if not Batch.query.filter_by(id=data["batch_id"], organization_id=org_id).first():
            return jsonify({"error": "Class not found"}), 404
        if not Subject.query.filter_by(id=data["subject_id"], organization_id=org_id).first():
            return jsonify({"error": "Subject not found"}), 404
        teacher_id = data.get("teacher_id") or None
        if teacher_id and not Teacher.query.filter_by(id=teacher_id, organization_id=org_id).first():
            return jsonify({"error": "Teacher not found"}), 404

        pin = PinnedSlot(
            organization_id=org_id,
            batch_id=data["batch_id"],
            subject_id=data["subject_id"],
            teacher_id=teacher_id,
            day=data["day"],
            period_number=data["period_number"],
        )
        db.session.add(pin)
        db.session.commit()
        return jsonify(pin.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/admin/pinned-slots/<int:pin_id>", methods=["DELETE"])
@role_required("admin")
def delete_pinned_slot(pin_id):
    """Remove a pinned/fixed period."""
    try:
        pin = owned_or_404(PinnedSlot, pin_id)
        db.session.delete(pin)
        db.session.commit()
        return jsonify({"message": "Pinned slot removed"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TIMETABLE ENDPOINTS
# ============================================================================

# NOTE: All /api/timetable/* routes live in timetable_routes.py (blueprint
# `timetable_bp`): generate, list, <id> (GET/DELETE), <id>/publish,
# batch/<id>, validate, and conflicts/*. They run the real SchedulingEngine and
# are organization-scoped. Nothing under that prefix is defined here, so there
# is exactly one handler per timetable URL.


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
@role_required("admin", "principal")
def get_stats():
    """Get database statistics for the caller's organization"""
    return jsonify(get_db_stats(current_org_id())), 200


# NOTE: A public POST /api/seed endpoint used to live here. It shelled out to
# wipe and reseed the database with no authentication, so anyone could destroy
# all data. It has been removed. Seeding is a deliberate operational task run
# from the CLI instead, e.g.:
#     docker compose exec backend python seed_realistic.py


# ============================================================================
# PDF EXPORT ENDPOINTS
# ============================================================================

def _safe_filename_part(text):
    """Reduce arbitrary text to a filename-safe slug."""
    keep = [c if c.isalnum() else "-" for c in (text or "")]
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "timetable"


@api.route("/export/timetable/batch/<int:timetable_id>", methods=["GET"])
@token_required
@role_required(["admin", "principal"])
def export_batch_timetable(timetable_id):
    """Export timetable as PDF (class/batch-wise).

    Optional query param ?batch_id=<id> exports a single class; omitting it
    exports every class in the organization.
    """
    try:
        from pdf_utils import export_batch_timetable

        org_id = current_org_id()
        timetable = Timetable.query.filter_by(id=timetable_id, organization_id=org_id).first()
        if not timetable:
            return jsonify({"error": "Timetable not found"}), 404

        batch_id = request.args.get("batch_id", type=int)
        label = "all-classes"
        if batch_id is not None:
            batch = Batch.query.filter_by(id=batch_id, organization_id=org_id).first()
            if not batch:
                return jsonify({"error": "Class not found"}), 404
            label = _safe_filename_part(f"Grade-{batch.grade}-{batch.section}")

        org = Organization.query.get(org_id)
        pdf_buffer = export_batch_timetable(
            timetable_id,
            organization_id=org_id,
            school_name=(org.name if org else None) or timetable.school_name or "School",
            batch_id=batch_id,
        )

        return pdf_buffer.getvalue(), 200, {
            "Content-Disposition": f'attachment; filename="timetable_{label}.pdf"',
            "Content-Type": "application/pdf",
        }
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/export/timetable/teacher/<int:timetable_id>", methods=["GET"])
@token_required
@role_required(["admin", "principal", "teacher"])
def export_teacher_timetable(timetable_id):
    """Export timetable as PDF (teacher-wise).

    Optional query param ?teacher_id=<id> exports a single teacher; omitting it
    exports every teacher in the organization.
    """
    try:
        from pdf_utils import export_teacher_timetable

        org_id = current_org_id()
        timetable = Timetable.query.filter_by(id=timetable_id, organization_id=org_id).first()
        if not timetable:
            return jsonify({"error": "Timetable not found"}), 404

        teacher_id = request.args.get("teacher_id", type=int)
        label = "all-teachers"
        if teacher_id is not None:
            teacher = Teacher.query.filter_by(id=teacher_id, organization_id=org_id).first()
            if not teacher:
                return jsonify({"error": "Teacher not found"}), 404
            label = _safe_filename_part(teacher.teacher_code or teacher.name)

        org = Organization.query.get(org_id)
        pdf_buffer = export_teacher_timetable(
            timetable_id,
            organization_id=org_id,
            school_name=(org.name if org else None) or timetable.school_name or "School",
            teacher_id=teacher_id,
        )

        return pdf_buffer.getvalue(), 200, {
            "Content-Disposition": f'attachment; filename="timetable_{label}.pdf"',
            "Content-Type": "application/pdf",
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

        # Ensure the teacher belongs to the caller's organization.
        owned_or_404(Teacher, teacher_id)

        result = LeaveService.mark_teacher_absent(
            teacher_id, absent_date, approved_by=request.user.get("user_id")
        )
        
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
