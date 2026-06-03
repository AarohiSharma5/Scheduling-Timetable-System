"""
TIMETABLE CONFLICT DETECTION SYSTEM

Validates timetable schedules for constraint violations:
1. Teacher Double Booking - Same teacher in 2+ classes at same time
2. Duplicate Subject Slot - Same subject taught twice in same batch at same time
3. Batch Overlap - Same batch has 2+ subjects in same time slot
4. Teacher Workload - Teacher exceeds max_periods_per_week
5. Empty Gaps - Identify unscheduled periods for subjects/batches
6. Teacher-Batch Mismatch - Teacher teaching batch not assigned to them
"""

from typing import Dict, List, Tuple, Set
from models import db, Timetable, TimetableSlot, Teacher, Batch, Subject, SchoolConfig
from datetime import datetime


class ConflictReport:
    """Represents timetable validation results"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []  # Critical conflicts
        self.warnings = []  # Suboptimal but working
        self.gaps = []  # Unscheduled periods
        self.stats = {
            "total_slots": 0,
            "scheduled_slots": 0,
            "empty_slots": 0,
            "teachers_affected": 0,
            "batches_affected": 0,
        }
    
    def add_error(self, error_type: str, message: str, details: dict = None):
        """Add critical error"""
        self.is_valid = False
        self.errors.append({
            "type": error_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def add_warning(self, warning_type: str, message: str, details: dict = None):
        """Add non-critical warning"""
        self.warnings.append({
            "type": warning_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def add_gap(self, subject_name: str, batch_id: int, batch_name: str, periods_missing: int):
        """Add unscheduled period gap"""
        self.gaps.append({
            "subject": subject_name,
            "batch_id": batch_id,
            "batch_name": batch_name,
            "periods_missing": periods_missing,
        })
    
    def to_dict(self):
        """Convert to JSON-serializable format"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "gaps": self.gaps,
            "stats": self.stats,
            "summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "total_gaps": len(self.gaps),
                "conflict_free": self.is_valid,
            }
        }


class ConflictDetector:
    """Main conflict detection engine"""
    
    def __init__(self, timetable_id: int):
        self.timetable_id = timetable_id
        self.report = ConflictReport()
        self.timetable = None
        self.slots = []
        self.config = None
    
    def validate(self) -> ConflictReport:
        """Run all validations on timetable"""
        try:
            self._load_data()
            self._detect_teacher_double_booking()
            self._detect_duplicate_subject_slots()
            self._detect_batch_overlap()
            self._detect_workload_exceeded()
            self._detect_teacher_batch_mismatch()
            self._detect_empty_gaps()
            self._calculate_stats()
        except Exception as e:
            self.report.add_error(
                "VALIDATION_ERROR",
                f"Error during conflict detection: {str(e)}"
            )
        
        return self.report
    
    # ========================================================================
    # DATA LOADING
    # ========================================================================
    
    def _load_data(self):
        """Load timetable and configuration"""
        self.timetable = Timetable.query.get(self.timetable_id)
        if not self.timetable:
            raise ValueError(f"Timetable {self.timetable_id} not found")
        
        self.slots = TimetableSlot.query.filter_by(timetable_id=self.timetable_id).all()
        # Scope config to the timetable's own organization so validation uses
        # the correct school's period structure in a multi-tenant deployment.
        self.config = SchoolConfig.query.filter_by(
            organization_id=self.timetable.organization_id
        ).first()
        if not self.config:
            raise ValueError("School configuration not found")
    
    # ========================================================================
    # CONFLICT DETECTION: TEACHER DOUBLE BOOKING
    # ========================================================================
    
    def _detect_teacher_double_booking(self):
        """
        Detect: Same teacher teaching 2+ batches at same time
        
        Query: For each time slot (day, period), check if any teacher appears >1 time
        """
        # Group slots by (day, period_number) and teacher_id
        time_slot_teachers: Dict[Tuple[str, int], List] = {}
        
        for slot in self.slots:
            if not slot.teacher_id:
                continue
            
            key = (slot.day, slot.period_number)
            if key not in time_slot_teachers:
                time_slot_teachers[key] = []
            
            time_slot_teachers[key].append({
                "teacher_id": slot.teacher_id,
                "teacher_name": slot.teacher.name if slot.teacher else "Unknown",
                "batch_id": slot.batch_id,
                "batch_name": f"Grade {slot.batch.grade}-{slot.batch.section}" if slot.batch else "Unknown",
                "subject_name": slot.subject.name if slot.subject else "Unknown",
            })
        
        # Find teachers appearing multiple times in same slot
        for (day, period), assignments in time_slot_teachers.items():
            teacher_counts = {}
            for assignment in assignments:
                tid = assignment["teacher_id"]
                teacher_counts[tid] = teacher_counts.get(tid, 0) + 1
            
            # Report double bookings
            for teacher_id, count in teacher_counts.items():
                if count > 1:
                    teacher_assignments = [a for a in assignments if a["teacher_id"] == teacher_id]
                    self.report.add_error(
                        "TEACHER_DOUBLE_BOOKING",
                        f"Teacher {teacher_assignments[0]['teacher_name']} booked {count} times on {day} Period {period}",
                        {
                            "teacher_id": teacher_id,
                            "day": day,
                            "period": period,
                            "assignments": [
                                {
                                    "batch": a["batch_name"],
                                    "subject": a["subject_name"]
                                } for a in teacher_assignments
                            ]
                        }
                    )
    
    # ========================================================================
    # CONFLICT DETECTION: DUPLICATE SUBJECT SLOTS
    # ========================================================================
    
    def _detect_duplicate_subject_slots(self):
        """
        Detect: Same subject-batch pair scheduled multiple times at same time
        """
        subject_batch_slots = {}
        
        for slot in self.slots:
            if not slot.subject_id or not slot.batch_id:
                continue
            
            key = (slot.day, slot.period_number, slot.subject_id, slot.batch_id)
            if key not in subject_batch_slots:
                subject_batch_slots[key] = []
            subject_batch_slots[key].append(slot)
        
        # Find duplicates
        for (day, period, subject_id, batch_id), slots in subject_batch_slots.items():
            if len(slots) > 1:
                subject = Subject.query.get(subject_id)
                batch = Batch.query.get(batch_id)
                
                self.report.add_error(
                    "DUPLICATE_SUBJECT_SLOT",
                    f"Subject '{subject.name if subject else 'Unknown'}' scheduled {len(slots)} times for Grade {batch.grade}-{batch.section} on {day} Period {period}",
                    {
                        "subject_id": subject_id,
                        "batch_id": batch_id,
                        "day": day,
                        "period": period,
                        "count": len(slots),
                        "teacher_ids": [s.teacher_id for s in slots]
                    }
                )
    
    # ========================================================================
    # CONFLICT DETECTION: BATCH OVERLAP
    # ========================================================================
    
    def _detect_batch_overlap(self):
        """
        Detect: Same batch has 2+ subjects in same time slot (batch can't attend 2 classes)
        """
        batch_time_slots = {}
        
        for slot in self.slots:
            if not slot.batch_id:
                continue
            
            key = (slot.day, slot.period_number, slot.batch_id)
            if key not in batch_time_slots:
                batch_time_slots[key] = []
            batch_time_slots[key].append(slot)
        
        # Find overlaps
        for (day, period, batch_id), slots in batch_time_slots.items():
            if len(slots) > 1:
                batch = Batch.query.get(batch_id)
                
                self.report.add_error(
                    "BATCH_OVERLAP",
                    f"Batch Grade {batch.grade}-{batch.section} has {len(slots)} subjects on {day} Period {period}",
                    {
                        "batch_id": batch_id,
                        "day": day,
                        "period": period,
                        "subjects": [
                            {
                                "subject": s.subject.name if s.subject else "Unknown",
                                "teacher": s.teacher.name if s.teacher else "Unknown"
                            } for s in slots
                        ]
                    }
                )
    
    # ========================================================================
    # CONFLICT DETECTION: TEACHER WORKLOAD
    # ========================================================================
    
    def _detect_workload_exceeded(self):
        """
        Detect: Teacher assigned more periods than max_periods_per_week
        
        Query: COUNT(slots) per teacher WHERE teacher_id is not null GROUP BY teacher_id
        """
        # Count periods per teacher
        teacher_workload = {}
        
        for slot in self.slots:
            if not slot.teacher_id:
                continue
            
            if slot.teacher_id not in teacher_workload:
                teacher_workload[slot.teacher_id] = {
                    "count": 0,
                    "teacher_name": slot.teacher.name if slot.teacher else "Unknown",
                    "max_allowed": 0,
                }
            
            teacher_workload[slot.teacher_id]["count"] += 1
        
        # Get teacher max periods (scoped to this timetable's organization)
        for teacher in Teacher.query.filter_by(organization_id=self.timetable.organization_id).all():
            if teacher.id in teacher_workload:
                teacher_workload[teacher.id]["max_allowed"] = teacher.max_periods_per_week or 24
        
        # Report overloaded teachers
        for teacher_id, data in teacher_workload.items():
            if data["count"] > data["max_allowed"]:
                self.report.add_warning(
                    "TEACHER_OVERLOAD",
                    f"Teacher {data['teacher_name']} assigned {data['count']} periods (max: {data['max_allowed']})",
                    {
                        "teacher_id": teacher_id,
                        "assigned_periods": data["count"],
                        "max_allowed": data["max_allowed"],
                        "excess": data["count"] - data["max_allowed"]
                    }
                )
    
    # ========================================================================
    # CONFLICT DETECTION: TEACHER-BATCH MISMATCH
    # ========================================================================
    
    def _detect_teacher_batch_mismatch(self):
        """
        Detect: Teacher assigned to batch they're not explicitly assigned to
        """
        for slot in self.slots:
            if not slot.teacher_id or not slot.batch_id:
                continue
            
            teacher = Teacher.query.get(slot.teacher_id)
            batch = Batch.query.get(slot.batch_id)
            
            # Check if teacher is assigned to this batch
            if slot.batch_id not in (teacher.assigned_batch_ids or []):
                self.report.add_error(
                    "TEACHER_BATCH_MISMATCH",
                    f"Teacher '{teacher.name}' assigned to Grade {batch.grade}-{batch.section} but not in their assigned batches",
                    {
                        "teacher_id": slot.teacher_id,
                        "teacher_name": teacher.name,
                        "batch_id": slot.batch_id,
                        "batch_name": f"Grade {batch.grade}-{batch.section}",
                        "assigned_batches": teacher.assigned_batch_ids or []
                    }
                )
    
    # ========================================================================
    # CONFLICT DETECTION: EMPTY GAPS
    # ========================================================================
    
    def _detect_empty_gaps(self):
        """
        Detect: Subjects not meeting their required periods per week
        
        For each subject-batch pair:
            required = subject.periods_per_week
            scheduled = COUNT(slots WHERE subject_id AND batch_id)
            missing = required - scheduled
        """
        from models import Subject
        
        scheduled_periods = {}
        
        # Count scheduled periods per subject-batch pair
        for slot in self.slots:
            if not slot.subject_id or not slot.batch_id:
                continue
            
            key = (slot.subject_id, slot.batch_id)
            scheduled_periods[key] = scheduled_periods.get(key, 0) + 1
        
        # Check against requirements (scoped to this timetable's organization)
        for batch in Batch.query.filter_by(organization_id=self.timetable.organization_id).all():
            for subject_id in (batch.subject_ids or []):
                subject = Subject.query.get(subject_id)
                if not subject:
                    continue
                
                key = (subject_id, batch.id)
                scheduled = scheduled_periods.get(key, 0)
                required = subject.periods_per_week
                
                if scheduled < required:
                    missing = required - scheduled
                    self.report.add_gap(
                        subject.name,
                        batch.id,
                        f"Grade {batch.grade}-{batch.section}",
                        missing
                    )
                    
                    self.report.add_warning(
                        "INCOMPLETE_SCHEDULE",
                        f"Subject '{subject.name}' for Grade {batch.grade}-{batch.section}: {scheduled}/{required} periods scheduled",
                        {
                            "subject_id": subject_id,
                            "batch_id": batch.id,
                            "scheduled": scheduled,
                            "required": required,
                            "missing": missing
                        }
                    )
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def _calculate_stats(self):
        """Calculate timetable statistics"""
        self.report.stats["total_slots"] = len(self.slots)
        
        scheduled = sum(1 for s in self.slots if s.teacher_id and s.subject_id)
        self.report.stats["scheduled_slots"] = scheduled
        self.report.stats["empty_slots"] = len(self.slots) - scheduled
        
        # Teachers and batches affected by errors
        error_teachers = set()
        error_batches = set()
        
        for error in self.report.errors:
            if "teacher_id" in error.get("details", {}):
                error_teachers.add(error["details"]["teacher_id"])
            if "batch_id" in error.get("details", {}):
                error_batches.add(error["details"]["batch_id"])
        
        self.report.stats["teachers_affected"] = len(error_teachers)
        self.report.stats["batches_affected"] = len(error_batches)
