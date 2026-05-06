from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

# ============================================================================
# USER MODEL - Authentication & Role Management
# ============================================================================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'principal', 'teacher', 'student'
    password_hash = db.Column(db.String(255))  # For email/password auth
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))  # For students only
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "email": self.email, 
            "role": self.role,
            "batch_id": self.batch_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# BATCH MODEL - Grade/Section/Class
# ============================================================================
class Batch(db.Model):
    __tablename__ = "batches"
    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.String(20), nullable=False)  # e.g., "Grade 9", "10", "XII"
    section = db.Column(db.String(10), nullable=False)  # e.g., "A", "B", "C"
    student_count = db.Column(db.Integer, default=0)
    subject_ids = db.Column(db.JSON, default=list)  # List of subject IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "grade": self.grade,
            "section": self.section,
            "student_count": self.student_count,
            "subject_ids": self.subject_ids or [],
            "display_name": f"Grade {self.grade} - Section {self.section}",
        }


# ============================================================================
# SUBJECT MODEL - Subjects taught in school
# ============================================================================
class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    periods_per_week = db.Column(db.Integer, nullable=False)  # How many periods per week
    batch_ids = db.Column(db.JSON, default=list)  # Which batches need this subject
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "periods_per_week": self.periods_per_week,
            "batch_ids": self.batch_ids or [],
        }


# ============================================================================
# TEACHER MODEL - Teacher profiles
# ============================================================================
class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject_ids = db.Column(db.JSON, default=list)  # Subjects they teach
    assigned_batch_ids = db.Column(db.JSON, default=list)  # Batches assigned to them
    is_class_teacher = db.Column(db.Boolean, default=False)  # Class teacher of a section?
    class_teacher_batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))  # Which batch they're class teacher of
    has_duties = db.Column(db.Boolean, default=False)  # Has extra duties (sports, admin, etc.)?
    max_periods_per_week = db.Column(db.Integer)  # Max hours/periods per week (auto-calculated based on duties)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "subject_ids": self.subject_ids or [],
            "assigned_batch_ids": self.assigned_batch_ids or [],
            "is_class_teacher": self.is_class_teacher,
            "class_teacher_batch_id": self.class_teacher_batch_id,
            "has_duties": self.has_duties,
            "max_periods_per_week": self.max_periods_per_week,
        }


# ============================================================================
# SCHOOL CONFIG MODEL - School timing settings
# ============================================================================
class SchoolConfig(db.Model):
    __tablename__ = "school_config"
    id = db.Column(db.Integer, primary_key=True, default=1)  # Singleton
    start_time = db.Column(db.String(10), default="08:00")  # HH:MM format
    end_time = db.Column(db.String(10), default="15:00")
    lunch_start = db.Column(db.String(10), default="12:00")
    lunch_end = db.Column(db.String(10), default="13:00")
    period_duration = db.Column(db.Integer, default=45)  # minutes
    periods_per_day = db.Column(db.Integer, default=6)
    working_days = db.Column(db.Integer, default=5)  # Mon-Fri = 5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "lunch_start": self.lunch_start,
            "lunch_end": self.lunch_end,
            "period_duration": self.period_duration,
            "periods_per_day": self.periods_per_day,
            "working_days": self.working_days,
        }


# ============================================================================
# TIMETABLE SLOT MODEL - Individual timetable entries
# ============================================================================
class TimetableSlot(db.Model):
    __tablename__ = "timetable_slots"
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey("timetables.id"), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # "Monday", "Tuesday", etc.
    period_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, ...
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    is_lunch = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "day": self.day,
            "period_number": self.period_number,
            "batch_id": self.batch_id,
            "teacher_id": self.teacher_id,
            "subject_id": self.subject_id,
            "is_lunch": self.is_lunch,
        }


# ============================================================================
# TIMETABLE MODEL - Complete timetable record
# ============================================================================
class Timetable(db.Model):
    __tablename__ = "timetables"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="draft")  # 'draft', 'published', 'archived'
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    warnings = db.Column(db.JSON, default=list)  # Any constraint violations or warnings
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    slots = db.relationship("TimetableSlot", backref="timetable", lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self, include_slots=False):
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "warnings": self.warnings or [],
        }
        if include_slots:
            result["slots"] = [slot.to_dict() for slot in self.slots]
        return result
