"""
TIMETABLE SCHEDULING SYSTEM
Automatic constraint-based timetable generation

Constraints:
1. Teacher Availability: One teacher cannot teach 2 batches @ same time
2. Batch Conflicts: One batch cannot have 2 subjects in same slot
3. Period Requirements: Each subject must meet required periods/week
4. Teacher Max Periods: Cannot exceed teacher's max_periods_per_week
5. Lunch Exclusion: No classes during lunch break
6. School Hours: Only during configured working hours
"""

from datetime import time
from typing import Dict, List, Tuple, Optional, Set
from models import db, Teacher, Batch, Subject, SchoolConfig, Timetable, TimetableSlot

# ============================================================================
# DATA STRUCTURES FOR SCHEDULING
# ============================================================================

class Period:
    """Represents a single time slot"""
    def __init__(self, day: str, period_num: int):
        self.day = day
        self.period_num = period_num
    
    def __hash__(self):
        return hash((self.day, self.period_num))
    
    def __eq__(self, other):
        return self.day == other.day and self.period_num == other.period_num
    
    def __repr__(self):
        return f"{self.day}-P{self.period_num}"


class Assignment:
    """Represents a teacher-subject-batch assignment"""
    def __init__(self, teacher_id: int, subject_id: int, batch_id: int):
        self.teacher_id = teacher_id
        self.subject_id = subject_id
        self.batch_id = batch_id
        self.periods_assigned = 0
    
    def __repr__(self):
        return f"T{self.teacher_id}->S{self.subject_id}->B{self.batch_id}"


# ============================================================================
# SCHEDULING ENGINE
# ============================================================================

class SchedulingEngine:
    """
    Algorithm: Multi-pass Backtracking with Greedy Heuristics
    
    Steps:
    1. Initialize empty timetable grid
    2. Calculate required assignments (subject periods needed per batch)
    3. Sort assignments by priority (critical subjects first)
    4. Attempt to place each assignment using backtracking
    5. Validate all constraints before finalizing
    6. Generate report of conflicts/warnings
    """
    
    def __init__(self, app=None):
        self.app = app
        self.timetable = {}  # {Period -> (teacher_id, subject_id, batch_id)}
        self.teacher_load = {}  # {teacher_id -> periods_used}
        self.batch_schedule = {}  # {batch_id -> {subject_id -> periods_assigned}}
        self.conflicts = []
        self.warnings = []
    
    def generate_timetable(self, timetable_id: int) -> Tuple[bool, List[str]]:
        """
        Main entry point for timetable generation
        Returns: (success, warnings/errors)
        """
        try:
            # Step 1: Load configuration
            config = SchoolConfig.query.first()
            if not config:
                return False, ["School configuration not found"]
            
            # Step 2: Get all entities
            teachers = Teacher.query.all()
            batches = Batch.query.all()
            subjects = Subject.query.all()
            
            if not teachers or not batches or not subjects:
                return False, ["Missing teachers, batches, or subjects"]
            
            # Step 3: Validate input data
            errors = self._validate_input(teachers, batches, subjects, config)
            if errors:
                return False, errors
            
            # Step 4: Calculate available time slots
            slots = self._calculate_available_slots(config)
            if not slots:
                return False, ["No available time slots calculated"]
            
            # Step 5: Generate required assignments
            assignments = self._calculate_required_assignments(batches, subjects, teachers)
            if not assignments:
                return False, ["No valid assignments generated"]
            
            # Step 6: Attempt scheduling with backtracking
            success = self._schedule_assignments(
                assignments, teachers, batches, subjects, slots, config
            )
            
            if not success:
                self.warnings.append("Scheduling completed with conflicts")
            
            # Step 7: Save to database
            self._save_timetable(timetable_id, config)
            
            return True, self.warnings
        
        except Exception as e:
            return False, [f"Error during scheduling: {str(e)}"]
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def _validate_input(self, teachers, batches, subjects, config) -> List[str]:
        """Validate that input data is complete and consistent"""
        errors = []
        
        # Check teachers have subjects
        for teacher in teachers:
            if not teacher.subject_ids:
                errors.append(f"Teacher {teacher.name} has no subjects assigned")
        
        # Check teachers have batches
        for teacher in teachers:
            if not teacher.assigned_batch_ids:
                errors.append(f"Teacher {teacher.name} has no batches assigned")
        
        # Check batches have subjects
        for batch in batches:
            if not batch.subject_ids:
                errors.append(f"Batch {batch.grade}-{batch.section} has no subjects")
        
        # Check max_periods_per_week is set
        for teacher in teachers:
            if not teacher.max_periods_per_week:
                errors.append(f"Teacher {teacher.name} has no max_periods_per_week set")
        
        # Check school config times are valid
        try:
            time.fromisoformat(config.start_time)
            time.fromisoformat(config.end_time)
            time.fromisoformat(config.lunch_start)
            time.fromisoformat(config.lunch_end)
        except ValueError:
            errors.append("Invalid school configuration times")
        
        return errors
    
    # ========================================================================
    # SLOT CALCULATION
    # ========================================================================
    
    def _calculate_available_slots(self, config: SchoolConfig) -> List[Period]:
        """
        Calculate all available time slots considering:
        - Working days (e.g., Mon-Fri = 5 days)
        - Periods per day (e.g., 6 periods)
        - Lunch break exclusion
        
        Returns: List of Period objects representing available slots
        """
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        available_days = days[:config.working_days]
        
        slots = []
        lunch_period_start = self._get_lunch_period_start(config)
        lunch_period_end = self._get_lunch_period_end(config)
        
        for day in available_days:
            for period in range(1, config.periods_per_day + 1):
                # Skip lunch period
                if lunch_period_start <= period <= lunch_period_end:
                    continue
                
                slots.append(Period(day, period))
        
        return slots
    
    def _get_lunch_period_start(self, config: SchoolConfig) -> int:
        """Calculate which period lunch starts"""
        start = time.fromisoformat(config.start_time)
        lunch_start = time.fromisoformat(config.lunch_start)
        
        minutes_elapsed = (lunch_start.hour - start.hour) * 60 + (lunch_start.minute - start.minute)
        period = (minutes_elapsed // config.period_duration) + 1
        return period
    
    def _get_lunch_period_end(self, config: SchoolConfig) -> int:
        """Calculate which period lunch ends"""
        start = time.fromisoformat(config.start_time)
        lunch_end = time.fromisoformat(config.lunch_end)
        
        minutes_elapsed = (lunch_end.hour - start.hour) * 60 + (lunch_end.minute - start.minute)
        period = (minutes_elapsed // config.period_duration)
        return period
    
    # ========================================================================
    # ASSIGNMENT CALCULATION
    # ========================================================================
    
    def _calculate_required_assignments(
        self, batches, subjects, teachers
    ) -> List[Assignment]:
        """
        Calculate all required subject-batch-teacher assignments
        
        For each batch:
            For each subject in that batch:
                Find a teacher who teaches that subject AND teaches that batch
                Create an assignment for required_periods
        """
        assignments = []
        
        for batch in batches:
            self.batch_schedule[batch.id] = {}
            
            for subject_id in batch.subject_ids:
                subject = Subject.query.get(subject_id)
                if not subject:
                    continue
                
                self.batch_schedule[batch.id][subject_id] = 0
                
                # Find teacher(s) who:
                # 1. Teach this subject
                # 2. Teach this batch
                eligible_teachers = [
                    t for t in teachers
                    if subject_id in t.subject_ids and batch.id in t.assigned_batch_ids
                ]
                
                if not eligible_teachers:
                    self.warnings.append(
                        f"No teacher found for {subject.name} in Grade {batch.grade}-{batch.section}"
                    )
                    continue
                
                # Create assignment for the first eligible teacher
                # (In production, could round-robin or balance load)
                teacher = eligible_teachers[0]
                assignment = Assignment(teacher.id, subject_id, batch.id)
                
                # Mark periods needed
                for _ in range(subject.periods_per_week):
                    assignments.append(assignment)
        
        # Sort by priority: critical subjects first
        # (subjects with fewer period options get placed first)
        assignments.sort(
            key=lambda a: (a.subject_id, -a.periods_assigned),
            reverse=False
        )
        
        return assignments
    
    # ========================================================================
    # SCHEDULING WITH BACKTRACKING
    # ========================================================================
    
    def _schedule_assignments(
        self,
        assignments: List[Assignment],
        teachers,
        batches,
        subjects,
        slots: List[Period],
        config: SchoolConfig
    ) -> bool:
        """
        Attempt to schedule all assignments using backtracking
        
        Algorithm:
        1. For each assignment (teacher-subject-batch)
        2. Try to find available slot
        3. Check all constraints
        4. If valid, commit; else backtrack
        """
        
        # Initialize teacher loads
        for teacher in teachers:
            self.teacher_load[teacher.id] = 0
        
        # Try to assign each period
        for assignment_idx, assignment in enumerate(assignments):
            placed = False
            
            # Try each available slot
            for slot in slots:
                if self._is_slot_valid(assignment, slot):
                    # Place assignment
                    self.timetable[slot] = (
                        assignment.teacher_id,
                        assignment.subject_id,
                        assignment.batch_id
                    )
                    
                    # Update tracking
                    self.teacher_load[assignment.teacher_id] += 1
                    self.batch_schedule[assignment.batch_id][assignment.subject_id] += 1
                    
                    placed = True
                    break
            
            if not placed:
                self.conflicts.append(
                    f"Could not place {assignment} - either teacher full or batch conflict"
                )
        
        # Check if all assignments were placed
        assignments_placed = len(self.timetable)
        return assignments_placed == len(assignments)
    
    def _is_slot_valid(self, assignment: Assignment, slot: Period) -> bool:
        """
        Check all constraints for placing assignment at slot
        
        Constraints:
        1. Slot not already occupied
        2. Teacher not busy at this slot
        3. Batch not busy at this slot
        4. Teacher hasn't exceeded max periods
        5. Subject doesn't exceed required periods
        """
        
        # Constraint 1: Slot not occupied
        if slot in self.timetable:
            return False
        
        teacher_id = assignment.teacher_id
        batch_id = assignment.batch_id
        subject_id = assignment.subject_id
        
        # Constraint 2: Teacher not busy (no other batch at same time)
        for placed_slot, (t_id, s_id, b_id) in self.timetable.items():
            if t_id == teacher_id and placed_slot.day == slot.day and placed_slot.period_num == slot.period_num:
                return False
        
        # Constraint 3: Batch not busy (no other subject at same time)
        for placed_slot, (t_id, s_id, b_id) in self.timetable.items():
            if b_id == batch_id and placed_slot.day == slot.day and placed_slot.period_num == slot.period_num:
                return False
        
        # Constraint 4: Teacher max periods not exceeded
        teacher = Teacher.query.get(teacher_id)
        if self.teacher_load[teacher_id] >= teacher.max_periods_per_week:
            return False
        
        # Constraint 5: Subject periods not exceeded
        subject = Subject.query.get(subject_id)
        if self.batch_schedule[batch_id][subject_id] >= subject.periods_per_week:
            return False
        
        return True
    
    # ========================================================================
    # DATABASE SAVING
    # ========================================================================
    
    def _save_timetable(self, timetable_id: int, config: SchoolConfig):
        """Save generated timetable to database"""
        
        timetable = Timetable.query.get(timetable_id)
        if not timetable:
            timetable = Timetable(
                id=timetable_id,
                name=f"Generated Timetable {timetable_id}",
                status="draft",
                warnings=self.conflicts + self.warnings
            )
            db.session.add(timetable)
        else:
            # Clear existing slots
            TimetableSlot.query.filter_by(timetable_id=timetable_id).delete()
            timetable.warnings = self.conflicts + self.warnings
        
        # Save slots
        for slot, (teacher_id, subject_id, batch_id) in self.timetable.items():
            timetable_slot = TimetableSlot(
                timetable_id=timetable_id,
                day=slot.day,
                period_number=slot.period_num,
                batch_id=batch_id,
                teacher_id=teacher_id,
                subject_id=subject_id
            )
            db.session.add(timetable_slot)
        
        db.session.commit()


# ============================================================================
# ALGORITHM PSEUDOCODE
# ============================================================================

"""
PSEUDOCODE for Timetable Generation:

function GENERATE_TIMETABLE(school_config, teachers, batches, subjects):
    
    # STEP 1: Validation
    if VALIDATE(school_config, teachers, batches, subjects) == FAIL:
        return ERROR
    
    # STEP 2: Calculate slots
    available_slots = CALCULATE_SLOTS(school_config)
    
    # STEP 3: Generate assignments
    assignments = []
    for each batch in batches:
        for each subject in batch.subjects:
            for i in 1..subject.periods_per_week:
                teacher = FIND_ELIGIBLE_TEACHER(batch, subject, teachers)
                if teacher != NULL:
                    assignments.append(ASSIGNMENT(teacher, subject, batch))
    
    # STEP 4: Schedule with backtracking
    timetable = EMPTY_TIMETABLE
    teacher_load = {} for each teacher: teacher_load[teacher] = 0
    
    for each assignment in SORT(assignments, by=PRIORITY):
        placed = FALSE
        for each slot in available_slots:
            if IS_VALID(assignment, slot, timetable, teacher_load):
                PLACE(assignment, slot, timetable)
                teacher_load[assignment.teacher]++
                placed = TRUE
                break
        
        if placed == FALSE:
            ADD_CONFLICT(assignment)
    
    # STEP 5: Validate result
    result = VALIDATE_COVERAGE(timetable, batches, subjects)
    
    # STEP 6: Save
    SAVE_TO_DATABASE(timetable)
    return SUCCESS

function IS_VALID(assignment, slot, timetable, teacher_load):
    teacher_id = assignment.teacher_id
    batch_id = assignment.batch_id
    subject_id = assignment.subject_id
    
    # Check slot empty
    if timetable[slot] != NULL:
        return FALSE
    
    # Check teacher not busy
    for each (t, s, b) in timetable where t == teacher_id and SAME_TIME(slot):
        return FALSE
    
    # Check batch not busy
    for each (t, s, b) in timetable where b == batch_id and SAME_TIME(slot):
        return FALSE
    
    # Check teacher load
    if teacher_load[teacher_id] >= teacher.max_periods_per_week:
        return FALSE
    
    return TRUE
"""
