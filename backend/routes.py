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

from flask import Blueprint, request, jsonify
from models import db, User, Batch, Subject, Teacher, SchoolConfig, Timetable, TimetableSlot
from datetime import datetime, timedelta
from functools import wraps
import os

api = Blueprint("api", __name__, url_prefix="/api")

# ============================================================================
# MIDDLEWARE & HELPERS
# ============================================================================

def require_role(*roles):
    """Decorator to check user role"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # For now, accept any role (auth system to be implemented in Step 2)
            # TODO: Extract role from JWT token
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_db_stats():
    """Helper to get database statistics"""
    return {
        "users": User.query.count(),
        "batches": Batch.query.count(),
        "subjects": Subject.query.count(),
        "teachers": Teacher.query.count(),
        "timetables": Timetable.query.count(),
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

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
# AUTH ENDPOINTS (Step 2)
# ============================================================================

@api.route("/auth/login", methods=["POST"])
def login():
    """
    Login endpoint
    Body: { "email": "user@school.edu", "password": "password" }
    Returns: { "token": "jwt_token", "user": {...} }
    
    TODO: Implement JWT token generation in Step 2
    """
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
        
        # TODO: Check password hash
        return jsonify({
            "token": "mock_jwt_token_" + str(user.id),
            "user": user.to_dict(),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/auth/logout", methods=["POST"])
def logout():
    """Logout endpoint (token invalidation handled by frontend)"""
    return jsonify({"message": "Logged out"}), 200


# ============================================================================
# ADMIN ENDPOINTS - School Configuration
# ============================================================================

@api.route("/admin/school-config", methods=["GET"])
@require_role("admin", "principal")
def get_school_config():
    """Get current school configuration"""
    config = SchoolConfig.query.first() or SchoolConfig()
    return jsonify(config.to_dict()), 200


@api.route("/admin/school-config", methods=["POST"])
@require_role("admin")
def update_school_config():
    """Update school configuration"""
    try:
        data = request.get_json()
        config = SchoolConfig.query.first() or SchoolConfig(id=1)
        
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
@require_role("admin", "principal")
def get_teachers():
    """List all teachers"""
    teachers = Teacher.query.all()
    return jsonify([t.to_dict() for t in teachers]), 200


@api.route("/admin/teachers", methods=["POST"])
@require_role("admin")
def create_teacher():
    """Create a new teacher"""
    try:
        data = request.get_json()
        
        # Create user first
        user = User(
            name=data.get("name"),
            email=data.get("email"),
            role="teacher",
            password_hash="hashed_password_here",  # TODO: Hash actual password
        )
        db.session.add(user)
        db.session.commit()
        
        # Create teacher record
        teacher = Teacher(
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
        return jsonify({"error": str(e)}), 500


@api.route("/admin/teachers/<int:teacher_id>", methods=["GET"])
@require_role("admin", "principal")
def get_teacher(teacher_id):
    """Get a specific teacher"""
    teacher = Teacher.query.get_or_404(teacher_id)
    return jsonify(teacher.to_dict()), 200


@api.route("/admin/teachers/<int:teacher_id>", methods=["PUT"])
@require_role("admin")
def update_teacher(teacher_id):
    """Update a teacher"""
    try:
        teacher = Teacher.query.get_or_404(teacher_id)
        data = request.get_json()
        
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
@require_role("admin")
def delete_teacher(teacher_id):
    """Delete a teacher"""
    try:
        teacher = Teacher.query.get_or_404(teacher_id)
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
# ADMIN ENDPOINTS - Batch Management
# ============================================================================

@api.route("/admin/batches", methods=["GET"])
@require_role("admin", "principal")
def get_batches():
    """List all batches"""
    batches = Batch.query.all()
    return jsonify([b.to_dict() for b in batches]), 200


@api.route("/admin/batches", methods=["POST"])
@require_role("admin")
def create_batch():
    """Create a new batch"""
    try:
        data = request.get_json()
        batch = Batch(
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
@require_role("admin", "principal")
def get_batch(batch_id):
    """Get a specific batch"""
    batch = Batch.query.get_or_404(batch_id)
    return jsonify(batch.to_dict()), 200


@api.route("/admin/batches/<int:batch_id>", methods=["PUT"])
@require_role("admin")
def update_batch(batch_id):
    """Update a batch"""
    try:
        batch = Batch.query.get_or_404(batch_id)
        data = request.get_json()
        
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
@require_role("admin")
def delete_batch(batch_id):
    """Delete a batch"""
    try:
        batch = Batch.query.get_or_404(batch_id)
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
@require_role("admin", "principal")
def get_subjects():
    """List all subjects"""
    subjects = Subject.query.all()
    return jsonify([s.to_dict() for s in subjects]), 200


@api.route("/admin/subjects", methods=["POST"])
@require_role("admin")
def create_subject():
    """Create a new subject"""
    try:
        data = request.get_json()
        subject = Subject(
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
@require_role("admin", "principal")
def get_subject(subject_id):
    """Get a specific subject"""
    subject = Subject.query.get_or_404(subject_id)
    return jsonify(subject.to_dict()), 200


@api.route("/admin/subjects/<int:subject_id>", methods=["PUT"])
@require_role("admin")
def update_subject(subject_id):
    """Update a subject"""
    try:
        subject = Subject.query.get_or_404(subject_id)
        data = request.get_json()
        
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
@require_role("admin")
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        subject = Subject.query.get_or_404(subject_id)
        db.session.delete(subject)
        db.session.commit()
        return jsonify({"message": "Subject deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TIMETABLE ENDPOINTS
# ============================================================================

@api.route("/timetable/generate", methods=["POST"])
@require_role("admin")
def generate_timetable():
    """
    Generate a new timetable
    Body: { "name": "Week 1", "description": "..." }
    Returns: Generated timetable with slots
    
    TODO: Implement actual timetable generation algorithm in Step 5
    """
    try:
        data = request.get_json()
        
        # Create timetable record
        timetable = Timetable(
            name=data.get("name", "Generated Timetable"),
            description=data.get("description", ""),
            status="draft",
        )
        db.session.add(timetable)
        db.session.commit()
        
        # TODO: Call timetable generation algorithm here
        
        return jsonify({
            "message": "Timetable generation started",
            "timetable_id": timetable.id,
            "timetable": timetable.to_dict(),
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api.route("/timetable", methods=["GET"])
@require_role("admin", "principal", "teacher", "student")
def get_timetables():
    """List all timetables"""
    timetables = Timetable.query.order_by(Timetable.generated_at.desc()).all()
    return jsonify([t.to_dict() for t in timetables]), 200


@api.route("/timetable/<int:timetable_id>", methods=["GET"])
@require_role("admin", "principal", "teacher", "student")
def get_timetable(timetable_id):
    """Get a specific timetable with all slots"""
    timetable = Timetable.query.get_or_404(timetable_id)
    return jsonify(timetable.to_dict(include_slots=True)), 200


@api.route("/timetable/<int:timetable_id>/publish", methods=["POST"])
@require_role("admin")
def publish_timetable(timetable_id):
    """Publish a timetable"""
    try:
        timetable = Timetable.query.get_or_404(timetable_id)
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
@require_role("teacher")
def get_teacher_timetable():
    """Get the current user's timetable (teacher view)"""
    # TODO: Extract teacher_id from JWT token
    teacher_id = request.args.get("teacher_id")
    timetable_id = request.args.get("timetable_id")
    
    if not teacher_id or not timetable_id:
        return jsonify({"error": "teacher_id and timetable_id required"}), 400
    
    teacher = Teacher.query.get_or_404(teacher_id)
    timetable = Timetable.query.get_or_404(timetable_id)
    
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
@require_role("student")
def get_student_timetable():
    """Get the current user's batch timetable (student view)"""
    # TODO: Extract batch_id from JWT token (or user's batch_id)
    batch_id = request.args.get("batch_id")
    timetable_id = request.args.get("timetable_id")
    
    if not batch_id or not timetable_id:
        return jsonify({"error": "batch_id and timetable_id required"}), 400
    
    batch = Batch.query.get_or_404(batch_id)
    timetable = Timetable.query.get_or_404(timetable_id)
    
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
@require_role("principal")
def get_principal_dashboard():
    """Get principal dashboard data"""
    timetable_id = request.args.get("timetable_id")
    
    try:
        teachers = Teacher.query.all()
        batches = Batch.query.all()
        
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
        
        return jsonify({
            "teachers": [t.to_dict() for t in teachers],
            "batches": [b.to_dict() for b in batches],
            "teacher_workload": teacher_workload,
            "timetable": Timetable.query.get(timetable_id).to_dict() if timetable_id else None,
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
