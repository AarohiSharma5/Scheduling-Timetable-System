from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


# ============================================================================
# ORGANIZATION MODEL - Tenant / Institute level account
# ============================================================================
class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "logo_url": self.logo_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# USER MODEL - Authentication & Role Management
# ============================================================================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
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
            "organization_id": self.organization_id,
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
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    grade = db.Column(db.String(20), nullable=False)  # e.g., "Grade 9", "10", "XII"
    section = db.Column(db.String(10), nullable=False)  # e.g., "A", "B", "C"
    student_count = db.Column(db.Integer, default=0)
    subject_ids = db.Column(db.JSON, default=list)  # List of subject IDs
    # Optional per-class day length. null = use the school-wide number of periods.
    # Lets younger grades finish earlier than seniors (e.g. pre-primary = 4 periods).
    periods_per_day = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "grade": self.grade,
            "section": self.section,
            "student_count": self.student_count,
            "subject_ids": self.subject_ids or [],
            "periods_per_day": self.periods_per_day,
            "display_name": f"Grade {self.grade} - Section {self.section}",
        }


# ============================================================================
# SUBJECT MODEL - Subjects taught in school
# ============================================================================
class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    name = db.Column(db.String(120), nullable=False)
    periods_per_week = db.Column(db.Integer, nullable=False)  # How many periods per week
    # Spacing rule: max periods of this subject a batch may have on a single day
    # (default 1 prevents the same subject appearing twice/back-to-back in a day).
    max_periods_per_day = db.Column(db.Integer, nullable=False, default=1)
    # Lab/double subjects are scheduled as consecutive double periods.
    requires_double = db.Column(db.Boolean, nullable=False, default=False)
    batch_ids = db.Column(db.JSON, default=list)  # Which batches need this subject
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "periods_per_week": self.periods_per_week,
            "max_periods_per_day": self.max_periods_per_day,
            "requires_double": self.requires_double,
            "batch_ids": self.batch_ids or [],
        }


# ============================================================================
# PINNED SLOT MODEL - Fixed/locked periods the scheduler must honor
# ============================================================================
class PinnedSlot(db.Model):
    """A period the admin locks in advance (e.g. assembly, fixed lab, library).

    The scheduler places these first and works the rest of the timetable around
    them. teacher_id is optional — if omitted, an eligible teacher is chosen.
    """
    __tablename__ = "pinned_slots"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))  # optional
    day = db.Column(db.String(20), nullable=False)  # "Monday", ...
    period_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "subject_id": self.subject_id,
            "teacher_id": self.teacher_id,
            "day": self.day,
            "period_number": self.period_number,
        }


# ============================================================================
# TEACHER MODEL - Teacher profiles
# ============================================================================
class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    teacher_code = db.Column(db.String(50), index=True)  # Human-readable employee id, e.g. "TCHR0001"
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject_ids = db.Column(db.JSON, default=list)  # Flat list of subjects (derived from teaching_assignments)
    assigned_batch_ids = db.Column(db.JSON, default=list)  # Flat list of batches (derived from teaching_assignments)
    # Structured "what do they teach to whom": one entry per subject, each listing
    # the batches that subject is taught to, e.g.
    #   [{"subject_id": 1, "batch_ids": [9, 8]}, {"subject_id": 3, "batch_ids": [9]}]
    # This is the source of truth for eligibility; subject_ids/assigned_batch_ids
    # are kept in sync for backward compatibility.
    teaching_assignments = db.Column(db.JSON, default=list)
    # Non-teaching duties that consume weekly contact hours, e.g.
    #   [{"charge_id": 2, "name": "House Charge", "hours_per_week": 3}]
    charges = db.Column(db.JSON, default=list)
    # Hard availability constraint: slots the teacher cannot teach, as a list of
    # {"day": "Monday", "period": 1}. The scheduler never places them here.
    unavailable_slots = db.Column(db.JSON, default=list)
    is_class_teacher = db.Column(db.Boolean, default=False)  # Class teacher of a section?
    class_teacher_batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))  # Which batch they're class teacher of
    has_duties = db.Column(db.Boolean, default=False)  # Has extra duties (sports, admin, etc.)?
    # Max teaching periods/week. Computed dynamically as
    #   target_contact_periods_per_week - sum(charge hours)
    # so a teacher with charges teaches fewer classes but carries the same total load.
    max_periods_per_week = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def charge_hours(self):
        """Total weekly contact hours consumed by non-teaching charges."""
        total = 0
        for c in (self.charges or []):
            try:
                total += int(c.get("hours_per_week") or 0)
            except (AttributeError, TypeError, ValueError):
                continue
        return total

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "teacher_code": self.teacher_code,
            "name": self.name,
            "email": self.email,
            "subject_ids": self.subject_ids or [],
            "assigned_batch_ids": self.assigned_batch_ids or [],
            "teaching_assignments": self.teaching_assignments or [],
            "charges": self.charges or [],
            "charge_hours": self.charge_hours,
            "unavailable_slots": self.unavailable_slots or [],
            "is_class_teacher": self.is_class_teacher,
            "class_teacher_batch_id": self.class_teacher_batch_id,
            "has_duties": self.has_duties,
            "max_periods_per_week": self.max_periods_per_week,
        }


# ============================================================================
# TEACHER PREFERENCE MODEL - Soft preferences + workload targets
# ============================================================================
class TeacherPreference(db.Model):
    """Optional, *soft* scheduling preferences for a teacher.

    The scheduler tries to satisfy these (via a weighted score) but will violate
    them when the timetable would otherwise be impossible. One row per teacher.
    """
    __tablename__ = "teacher_preferences"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, unique=True, index=True)

    preferred_classes = db.Column(db.JSON, default=list)   # list of batch ids
    preferred_subjects = db.Column(db.JSON, default=list)  # list of subject ids
    preferred_slots = db.Column(db.JSON, default=list)     # ["morning","midday","last"] and/or period numbers
    blocked_slots = db.Column(db.JSON, default=list)       # [{"day": "Monday", "period": 1}] (hard, merged with Teacher.unavailable_slots)
    max_periods_day = db.Column(db.Integer)                # soft daily target
    max_periods_week = db.Column(db.Integer)               # soft weekly target
    allow_class_teacher_charge = db.Column(db.Boolean, nullable=False, default=True)
    allow_extra_charge = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "preferred_classes": self.preferred_classes or [],
            "preferred_subjects": self.preferred_subjects or [],
            "preferred_slots": self.preferred_slots or [],
            "blocked_slots": self.blocked_slots or [],
            "max_periods_day": self.max_periods_day,
            "max_periods_week": self.max_periods_week,
            "allow_class_teacher_charge": self.allow_class_teacher_charge,
            "allow_extra_charge": self.allow_extra_charge,
        }


# ============================================================================
# CHARGE MODEL - Catalog of non-teaching duties (class teacher, clubs, houses…)
# ============================================================================
class Charge(db.Model):
    """A reusable, admin-defined non-teaching duty with a default weekly load.

    Charges are assigned to teachers (see Teacher.charges); the hours they carry
    reduce the teacher's teaching capacity so total contact hours stay balanced.
    """
    __tablename__ = "charges"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    name = db.Column(db.String(120), nullable=False)
    default_hours_per_week = db.Column(db.Integer, nullable=False, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "default_hours_per_week": self.default_hours_per_week,
        }


# ============================================================================
# SCHOOL CONFIG MODEL - School timing settings
# ============================================================================
class SchoolConfig(db.Model):
    __tablename__ = "school_config"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    start_time = db.Column(db.String(10), default="08:00")  # HH:MM format
    end_time = db.Column(db.String(10), default="15:00")
    lunch_start = db.Column(db.String(10), default="12:00")
    lunch_end = db.Column(db.String(10), default="13:00")
    period_duration = db.Column(db.Integer, default=45)  # minutes
    periods_per_day = db.Column(db.Integer, default=6)  # derived from hours/duration on save
    # When True, one period is reserved for lunch; when False the day is compact
    # (back-to-back classes), which is common for younger grades / many schools.
    has_lunch_break = db.Column(db.Boolean, nullable=False, default=True)
    working_days = db.Column(db.Integer, default=5)  # Mon-Fri = 5
    # The common total weekly contact load every teacher is balanced to:
    #   teaching periods + charge hours == target. Used to derive each teacher's
    #   max teaching periods dynamically.
    target_contact_periods_per_week = db.Column(db.Integer, nullable=False, default=40)
    # Extra weekly contact hours reserved for class teachers. Defaults to 5/week
    # per organization; each org can edit it independently (it lives on the
    # org-scoped config, so other orgs keep their own value).
    class_teacher_hours_per_week = db.Column(db.Integer, nullable=False, default=5)
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
            "has_lunch_break": self.has_lunch_break,
            "working_days": self.working_days,
            "target_contact_periods_per_week": self.target_contact_periods_per_week or 40,
            "class_teacher_hours_per_week": (self.class_teacher_hours_per_week
                                             if self.class_teacher_hours_per_week is not None else 5),
        }


# ============================================================================
# TIMETABLE SLOT MODEL - Individual timetable entries
# ============================================================================
class TimetableSlot(db.Model):
    __tablename__ = "timetable_slots"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
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
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="draft")  # 'draft', 'published', 'archived'
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    warnings = db.Column(db.JSON, default=list)  # Any constraint violations or warnings
    school_name = db.Column(db.String(255))  # For PDF export header
    school_logo_path = db.Column(db.String(255))  # Path to logo image
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
            "school_name": self.school_name,
            "school_logo_path": self.school_logo_path,
        }
        if include_slots:
            result["slots"] = [slot.to_dict() for slot in self.slots]
        return result


# ============================================================================
# LEAVE REQUEST MODEL - Teacher leave management
# ============================================================================
class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    leave_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    leave_type = db.Column(db.String(50), default="sick")  # 'sick', 'casual', 'emergency', 'other'
    status = db.Column(db.String(20), default="pending")  # 'pending', 'approved', 'rejected'
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))  # Admin/Principal who approved
    substitute_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))  # Assigned substitute
    rejection_reason = db.Column(db.Text)  # Reason if rejected
    timetable_adjustments = db.Column(db.JSON, default=dict)  # How periods were rescheduled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "leave_date": self.leave_date.isoformat() if self.leave_date else None,
            "reason": self.reason,
            "leave_type": self.leave_type,
            "status": self.status,
            "approved_by": self.approved_by,
            "substitute_teacher_id": self.substitute_teacher_id,
            "rejection_reason": self.rejection_reason,
            "timetable_adjustments": self.timetable_adjustments or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# NOTIFICATION MODEL - User notifications
# ============================================================================
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'timetable_generated', 'timetable_updated', 'teacher_substituted', 'timing_changed', 'leave_approved', etc.
    related_id = db.Column(db.Integer)  # ID of related object (timetable_id, leave_request_id, etc.)
    is_read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(255))  # Where to redirect on click
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Auto-delete after expiration
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "related_id": self.related_id,
            "is_read": self.is_read,
            "action_url": self.action_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


# ============================================================================
# HOUSE MODEL - School Houses (for competitions, events)
# ============================================================================
class House(db.Model):
    __tablename__ = "houses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Red, Blue, Green, Yellow
    color = db.Column(db.String(50))  # HEX color code
    house_master_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))  # Teacher in charge
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "house_master_id": self.house_master_id,
        }


# ============================================================================
# STUDENT MODEL - Comprehensive student information
# ============================================================================
class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)  # STU0001
    admission_no = db.Column(db.String(50), unique=True, nullable=False)  # ADM240001
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # Link to auth User
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)  # Male, Female, Other
    date_of_birth = db.Column(db.Date, nullable=False)
    class_grade = db.Column(db.String(20), nullable=False)  # 1, 2, 7, 11 Science, 12 Commerce
    section = db.Column(db.String(10), nullable=False)  # A, B, C, D
    roll_no = db.Column(db.Integer)  # Roll number in class
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"))  # Which house assigned
    father_name = db.Column(db.String(120))
    mother_name = db.Column(db.String(120))
    contact_number = db.Column(db.String(20))
    address = db.Column(db.Text)
    transport_mode = db.Column(db.String(50), default="Private")  # Bus, Private, Walk
    blood_group = db.Column(db.String(10))  # A+, B-, etc.
    admission_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default="Active")  # Active, Inactive, Left, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "admission_no": self.admission_no,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "gender": self.gender,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "class_grade": self.class_grade,
            "section": self.section,
            "roll_no": self.roll_no,
            "house_id": self.house_id,
            "father_name": self.father_name,
            "mother_name": self.mother_name,
            "contact_number": self.contact_number,
            "address": self.address,
            "transport_mode": self.transport_mode,
            "blood_group": self.blood_group,
            "admission_date": self.admission_date.isoformat() if self.admission_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# CLASSROOM MODEL - Physical classroom resources
# ============================================================================
class Classroom(db.Model):
    __tablename__ = "classrooms"
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), unique=True, nullable=False)  # R101, R201, etc.
    room_name = db.Column(db.String(120), nullable=False)  # "Classroom 5A", "Physics Lab"
    capacity = db.Column(db.Integer, nullable=False)  # Max students
    room_type = db.Column(db.String(100), nullable=False)  # Classroom, Lab, Library, Hall, Activity
    assigned_class = db.Column(db.String(20))  # Which class uses this as primary room (e.g., "5A")
    facilities = db.Column(db.JSON, default=list)  # ["Projector", "AC", "Smart Board"]
    floor = db.Column(db.Integer)  # Ground floor, 1st floor, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "room_name": self.room_name,
            "capacity": self.capacity,
            "room_type": self.room_type,
            "assigned_class": self.assigned_class,
            "facilities": self.facilities or [],
            "floor": self.floor,
        }


# ============================================================================
# PRINCIPAL MODEL - School principal information
# ============================================================================
class Principal(db.Model):
    __tablename__ = "principals"
    id = db.Column(db.Integer, primary_key=True)
    principal_id = db.Column(db.String(50), unique=True, nullable=False)  # P001
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)  # Link to auth User
    name = db.Column(db.String(120), nullable=False)
    qualification = db.Column(db.String(200))  # PhD Education, M.A, etc.
    experience_years = db.Column(db.Integer)
    email = db.Column(db.String(120), unique=True)
    joining_date = db.Column(db.Date)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "principal_id": self.principal_id,
            "user_id": self.user_id,
            "name": self.name,
            "qualification": self.qualification,
            "experience_years": self.experience_years,
            "email": self.email,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "phone": self.phone,
        }


# ============================================================================
# COORDINATOR MODEL - Academic coordinators
# ============================================================================
class Coordinator(db.Model):
    __tablename__ = "coordinators"
    id = db.Column(db.Integer, primary_key=True)
    coordinator_id = db.Column(db.String(50), unique=True, nullable=False)  # C001
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)  # Link to auth User
    name = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(120), nullable=False)  # Pre Primary Coordinator, etc.
    responsibility = db.Column(db.Text)  # Classes 1-5, Nursery-UKG, etc.
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "coordinator_id": self.coordinator_id,
            "user_id": self.user_id,
            "name": self.name,
            "designation": self.designation,
            "responsibility": self.responsibility,
            "email": self.email,
            "phone": self.phone,
        }


# ============================================================================
# SUBJECT MASTER MODEL - Comprehensive subject definitions
# ============================================================================
class SubjectMaster(db.Model):
    __tablename__ = "subject_masters"
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.String(50), unique=True, nullable=False)  # SUB01, SUB02
    subject_name = db.Column(db.String(120), nullable=False)  # English, Hindi, etc.
    subject_code = db.Column(db.String(20), unique=True)  # ENG, HIN, MTH
    subject_type = db.Column(db.String(50), nullable=False)  # Core, Language, Practical, Activity, Elective
    min_periods_per_week = db.Column(db.Integer, default=1)
    max_periods_per_week = db.Column(db.Integer, default=8)
    applicable_classes = db.Column(db.JSON, default=list)  # ["1", "2", "3", ...] or ["11 Science", "12 Science"]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "subject_name": self.subject_name,
            "subject_code": self.subject_code,
            "subject_type": self.subject_type,
            "min_periods_per_week": self.min_periods_per_week,
            "max_periods_per_week": self.max_periods_per_week,
            "applicable_classes": self.applicable_classes or [],
        }
