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
from models import db, Teacher, Batch, Subject, SchoolConfig, Timetable, TimetableSlot, PinnedSlot, TeacherPreference

# ---------------------------------------------------------------------------
# Soft-preference / workload scoring weights. Higher = more desirable slot.
# These are *soft*: a low score never blocks a placement, it only influences
# which valid slot is chosen, so a feasible timetable is always produced.
# ---------------------------------------------------------------------------
W_PREFERRED_CLASS = 10
W_PREFERRED_SUBJECT = 8
W_PREFERRED_PERIOD = 6
P_FOUR_CONSECUTIVE = -12     # creating a 4th (or longer) back-to-back period
P_THREE_CONSECUTIVE = -5     # mild nudge away from 3 in a row
P_NO_BREAK_HALF_DAY = -8     # teaching a full half-day with no gap
P_OVER_SOFT_DAY = -15        # exceeding the soft per-day workload target
P_OVER_SOFT_WEEK = -10       # exceeding the soft per-week workload target
W_LIGHTER_DAY = -2           # per period already taught that day (spreads load)
DEFAULT_SOFT_PERIODS_DAY = 6 # fallback soft daily cap when teacher sets none

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


class Requirement:
    """One (batch, subject) teaching need: a chosen teacher and weekly periods.

    is_double marks lab/double subjects that must be placed as consecutive pairs.
    """
    def __init__(self, teacher_id: int, subject_id: int, batch_id: int,
                 periods: int, is_double: bool):
        self.teacher_id = teacher_id
        self.subject_id = subject_id
        self.batch_id = batch_id
        self.periods = periods
        self.is_double = is_double

    def __repr__(self):
        kind = "DBL" if self.is_double else "SGL"
        return f"{kind} T{self.teacher_id}->S{self.subject_id}->B{self.batch_id}x{self.periods}"


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
    
    def __init__(self, app=None, organization_id=None):
        self.app = app
        self.organization_id = organization_id
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
            org_id = self.organization_id

            # Step 1: Load configuration (scoped to this organization)
            config_q = SchoolConfig.query
            if org_id is not None:
                config_q = config_q.filter_by(organization_id=org_id)
            config = config_q.first()
            if not config:
                return False, ["School configuration not found"]
            
            # Step 2: Get all entities, scoped to this organization
            teacher_q, batch_q, subject_q = Teacher.query, Batch.query, Subject.query
            if org_id is not None:
                teacher_q = teacher_q.filter_by(organization_id=org_id)
                batch_q = batch_q.filter_by(organization_id=org_id)
                subject_q = subject_q.filter_by(organization_id=org_id)
            teachers = teacher_q.all()
            batches = batch_q.all()
            subjects = subject_q.all()
            
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

            # Index slots for fast lookups + consecutive-period (double) search.
            self._index_slots(slots)

            # Per-class day length (younger grades finish earlier) + lunch info,
            # used by constraint checks and when saving the grid.
            from period_utils import batch_period_count, lunch_period_index, has_lunch
            self.config = config
            self.batch_periods = {b.id: batch_period_count(b, config) for b in batches}
            self.lunch_idx = lunch_period_index(config)
            self.lunch_enabled = has_lunch(config)

            # Step 5: Build per-teacher/subject constraint caches.
            self._setup_caches(teachers, subjects)

            # Step 6: Generate the (batch, subject) requirements.
            requirements = self._calculate_requirements(batches, subjects, teachers)
            if not requirements:
                return False, ["No valid assignments generated"]

            # Step 7: Place admin-locked (pinned) periods first, then schedule
            # everything else around them honoring availability, spacing and
            # double-period rules.
            self._place_pinned(teachers)
            self._schedule_requirements(requirements)

            if self.conflicts:
                self.warnings.append("Scheduling completed with conflicts")

            # Step 8: Save to database
            self._save_timetable(timetable_id, config)

            return True, self.warnings
        
        except Exception as e:
            return False, [f"Error during scheduling: {str(e)}"]
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def _validate_input(self, teachers, batches, subjects, config) -> List[str]:
        """Validate input data.

        Only genuinely fatal problems (missing config, or no usable data at all)
        are returned as errors. Individual teachers/batches that are not fully
        wired up are recorded as warnings and simply skipped during scheduling,
        so one unassigned teacher can no longer abort the entire run.
        """
        errors = []

        # Per-entity gaps are non-fatal: warn and skip.
        for teacher in teachers:
            if not teacher.subject_ids:
                self.warnings.append(f"Teacher {teacher.name} has no subjects assigned (skipped)")
            if not teacher.assigned_batch_ids:
                self.warnings.append(f"Teacher {teacher.name} has no batches assigned (skipped)")
            if not teacher.max_periods_per_week:
                self.warnings.append(f"Teacher {teacher.name} has no max periods set (defaulting to 24)")

        for batch in batches:
            if not batch.subject_ids:
                self.warnings.append(f"Batch {batch.grade}-{batch.section} has no subjects (skipped)")

        # Fatal: no usable data at all.
        if not teachers:
            errors.append("No teachers available")
        if not batches:
            errors.append("No batches available")
        if not subjects:
            errors.append("No subjects available")

        # Fatal: malformed school config times.
        try:
            time.fromisoformat(config.start_time)
            time.fromisoformat(config.end_time)
            time.fromisoformat(config.lunch_start)
            time.fromisoformat(config.lunch_end)
        except (ValueError, TypeError):
            errors.append("Invalid school configuration times")

        # Fatal: zero/negative structural values would divide-by-zero or
        # produce an empty grid further down.
        if not config.period_duration or config.period_duration <= 0:
            errors.append("School configuration period_duration must be greater than 0")
        if not config.periods_per_day or config.periods_per_day <= 0:
            errors.append("School configuration periods_per_day must be greater than 0")
        if not config.working_days or config.working_days <= 0:
            errors.append("School configuration working_days must be greater than 0")

        return errors
    
    # ========================================================================
    # SLOT CALCULATION
    # ========================================================================
    
    def _calculate_available_slots(self, config: SchoolConfig) -> List[Period]:
        """All schedulable (day, period) slots for the full school day.

        Period count is derived from the school hours and period duration (so an
        08:00–14:00 day with 45-min periods always yields 8 slots), and the lunch
        period — if enabled — is excluded. Per-class day-length limits are applied
        later in `_can_place`.
        """
        from period_utils import build_layout, working_days

        days = working_days(config)
        slots = []
        for day in days:
            for row in build_layout(config):
                if row["is_lunch"]:
                    continue
                slots.append(Period(day, row["number"]))
        return slots
    
    # ========================================================================
    # ASSIGNMENT CALCULATION
    # ========================================================================
    
    def _index_slots(self, slots: List[Period]):
        """Index available slots for O(1) lookups and consecutive-period search."""
        self.slots = slots
        self.available = {(p.day, p.period_num) for p in slots}
        self.slots_by_day = {}
        self.days_in_order = []
        for p in slots:
            if p.day not in self.slots_by_day:
                self.slots_by_day[p.day] = []
                self.days_in_order.append(p.day)
            self.slots_by_day[p.day].append(p.period_num)
        for day in self.slots_by_day:
            self.slots_by_day[day].sort()

    def _setup_caches(self, teachers, subjects):
        """Build constraint lookup caches (teacher limits, availability, spacing)."""
        self.teacher_max = {t.id: (t.max_periods_per_week or 24) for t in teachers}
        self.subject_periods = {s.id: s.periods_per_week for s in subjects}
        self.subject_max_per_day = {
            s.id: (getattr(s, "max_periods_per_day", None) or 1) for s in subjects
        }
        self.subject_double = {
            s.id: bool(getattr(s, "requires_double", False)) for s in subjects
        }

        self.teacher_by_id = {t.id: t for t in teachers}

        # Precise "who can teach what to whom": set of (subject_id, batch_id) per
        # teacher. Built from structured teaching_assignments when present (so a
        # teacher can teach Maths to 9 & 8 but English only to 8), falling back to
        # the cartesian product of the flat subject/batch lists for older data.
        self.teacher_can_teach = {}
        for t in teachers:
            pairs = set()
            assignments = getattr(t, "teaching_assignments", None) or []
            if assignments:
                for a in assignments:
                    sid = a.get("subject_id")
                    for bid in (a.get("batch_ids") or []):
                        pairs.add((sid, bid))
            else:
                for sid in (t.subject_ids or []):
                    for bid in (t.assigned_batch_ids or []):
                        pairs.add((sid, bid))
            self.teacher_can_teach[t.id] = pairs

        # Load optional soft preferences (one row per teacher), scoped to org.
        self.prefs = {}
        pq = TeacherPreference.query
        if self.organization_id is not None:
            pq = pq.filter_by(organization_id=self.organization_id)
        for p in pq.all():
            self.prefs[p.teacher_id] = p

        # Teacher availability: set of (day, period) the teacher cannot teach.
        # This is HARD and merges Teacher.unavailable_slots with the (also hard)
        # blocked_slots from preferences.
        self.teacher_unavail = {}
        for t in teachers:
            blocked = set()
            pref = self.prefs.get(t.id)
            sources = list(t.unavailable_slots or [])
            if pref:
                sources += list(pref.blocked_slots or [])
            for entry in sources:
                try:
                    blocked.add((entry.get("day"), int(entry.get("period"))))
                except (AttributeError, TypeError, ValueError):
                    continue
            self.teacher_unavail[t.id] = blocked

        # Soft weekly target per teacher (preference overrides; falls back to the
        # hard weekly max). Used only for scoring, never to block a placement.
        self.soft_week = {}
        self.soft_day = {}
        for t in teachers:
            pref = self.prefs.get(t.id)
            self.soft_week[t.id] = (pref.max_periods_week if pref and pref.max_periods_week
                                    else (t.max_periods_per_week or 24))
            self.soft_day[t.id] = (pref.max_periods_day if pref and pref.max_periods_day
                                   else DEFAULT_SOFT_PERIODS_DAY)

        # Full school day length (periods), used for preferred-period categories
        # and the half-day no-break heuristic.
        self.school_periods = max((p.period_num for p in self.slots), default=1)

        self.teacher_load = {t.id: 0 for t in teachers}
        self.teacher_day_load = {}        # (teacher_id, day) -> periods that day
        self.occupied = set()             # (day, period, batch_id)
        self.teacher_busy = set()         # (teacher_id, day, period)
        self.batch_day_subject = {}       # (batch_id, day, subject_id) -> count

    # ========================================================================
    # ASSIGNMENT CALCULATION
    # ========================================================================

    def _calculate_requirements(self, batches, subjects, teachers) -> List[Requirement]:
        """Build one Requirement per (batch, subject) the batch needs."""
        subject_by_id = {s.id: s for s in subjects}
        requirements = []

        for batch in batches:
            self.batch_schedule[batch.id] = {}

            for subject_id in (batch.subject_ids or []):
                subject = subject_by_id.get(subject_id) or Subject.query.get(subject_id)
                if not subject:
                    continue

                self.batch_schedule[batch.id][subject_id] = 0

                eligible_teachers = [
                    t for t in teachers
                    if (subject_id, batch.id) in self.teacher_can_teach.get(t.id, ())
                ]
                if not eligible_teachers:
                    self.warnings.append(
                        f"No teacher found for {subject.name} in Grade {batch.grade}-{batch.section}"
                    )
                    continue

                # Soft preference at selection time: among eligible teachers,
                # favor one who has listed this class and/or subject as preferred.
                # Whichever teacher is chosen keeps the (batch, subject) for ALL
                # of its weekly periods, so a teacher assigned to a section teaches
                # that section consistently across the week.
                def _pref_rank(t):
                    p = self.prefs.get(t.id)
                    if not p:
                        return 0
                    rank = 0
                    if batch.id in (p.preferred_classes or []):
                        rank += 2
                    if subject_id in (p.preferred_subjects or []):
                        rank += 1
                    return rank

                eligible_teachers.sort(key=lambda t: (_pref_rank(t), -self.teacher_max.get(t.id, 24)), reverse=True)

                requirements.append(Requirement(
                    teacher_id=eligible_teachers[0].id,
                    subject_id=subject_id,
                    batch_id=batch.id,
                    periods=subject.periods_per_week,
                    is_double=self.subject_double.get(subject_id, False),
                ))

        # Hardest-to-place first: doubles, then by subject for determinism.
        requirements.sort(key=lambda r: (not r.is_double, r.subject_id))
        return requirements

    # ========================================================================
    # SCHEDULING
    # ========================================================================

    def _can_place(self, teacher_id, batch_id, subject_id, day, period, check_spacing=True) -> bool:
        """Whether (teacher, subject) can occupy (day, period) for a batch."""
        # Slot must exist (not lunch / within hours).
        if (day, period) not in self.available:
            return False
        # Per-class day length: junior grades stop after fewer periods.
        limit = self.batch_periods.get(batch_id)
        if limit is not None and period > limit:
            return False
        # Batch already busy this slot.
        if (day, period, batch_id) in self.occupied:
            return False
        # Teacher already teaching this slot.
        if (teacher_id, day, period) in self.teacher_busy:
            return False
        # Teacher availability (hard constraint).
        if (day, period) in self.teacher_unavail.get(teacher_id, ()):
            return False
        # Teacher weekly max.
        if self.teacher_load.get(teacher_id, 0) >= self.teacher_max.get(teacher_id, 24):
            return False
        # Subject weekly quota for this batch.
        if self.batch_schedule[batch_id].get(subject_id, 0) >= self.subject_periods.get(subject_id, 1):
            return False
        # Subject spacing: not too many of this subject in one day for the batch.
        if check_spacing:
            seen = self.batch_day_subject.get((batch_id, day, subject_id), 0)
            if seen >= self.subject_max_per_day.get(subject_id, 1):
                return False
        return True

    def _commit(self, teacher_id, subject_id, batch_id, day, period):
        """Record a placement in the timetable and all tracking caches."""
        slot = Period(day, period)
        self.timetable[(slot, batch_id)] = (teacher_id, subject_id, batch_id)
        self.occupied.add((day, period, batch_id))
        self.teacher_busy.add((teacher_id, day, period))
        self.teacher_load[teacher_id] = self.teacher_load.get(teacher_id, 0) + 1
        self.teacher_day_load[(teacher_id, day)] = self.teacher_day_load.get((teacher_id, day), 0) + 1
        self.batch_schedule[batch_id][subject_id] = self.batch_schedule[batch_id].get(subject_id, 0) + 1
        key = (batch_id, day, subject_id)
        self.batch_day_subject[key] = self.batch_day_subject.get(key, 0) + 1

    # ========================================================================
    # SOFT-PREFERENCE / WORKLOAD SCORING
    # ========================================================================

    def _period_category(self, period: int) -> str:
        """Map a period number to a time-of-day bucket: morning / midday / last."""
        n = max(self.school_periods, 1)
        if period <= n / 3.0:
            return "morning"
        if period <= 2.0 * n / 3.0:
            return "midday"
        return "last"

    def _consecutive_len(self, teacher_id, day, period) -> int:
        """Length of the back-to-back teaching run that would include (day, period)."""
        length = 1
        p = period - 1
        while (teacher_id, day, p) in self.teacher_busy:
            length += 1
            p -= 1
        p = period + 1
        while (teacher_id, day, p) in self.teacher_busy:
            length += 1
            p += 1
        return length

    def _score_slot(self, teacher_id, batch_id, subject_id, day, period) -> float:
        """Weighted desirability of placing (teacher, subject, batch) at (day, period).

        Purely advisory: only valid (hard-constraint-passing) slots are scored, so
        a low score never prevents a placement, it only ranks the choices.
        """
        score = 0.0
        pref = self.prefs.get(teacher_id)

        # --- Soft preferences ---
        if pref:
            if batch_id in (pref.preferred_classes or []):
                score += W_PREFERRED_CLASS
            if subject_id in (pref.preferred_subjects or []):
                score += W_PREFERRED_SUBJECT
            wanted = pref.preferred_slots or []
            if self._period_category(period) in wanted or period in wanted:
                score += W_PREFERRED_PERIOD

        # --- Workload balancing ---
        run = self._consecutive_len(teacher_id, day, period)
        if run >= 4:
            score += P_FOUR_CONSECUTIVE
        elif run == 3:
            score += P_THREE_CONSECUTIVE

        # No break in a half-day: a run spanning at least half the day's periods.
        if run >= max(2, (self.school_periods + 1) // 2):
            score += P_NO_BREAK_HALF_DAY

        # Soft daily / weekly targets (exceeding is allowed but discouraged).
        day_load = self.teacher_day_load.get((teacher_id, day), 0)
        if day_load + 1 > self.soft_day.get(teacher_id, DEFAULT_SOFT_PERIODS_DAY):
            score += P_OVER_SOFT_DAY
        if self.teacher_load.get(teacher_id, 0) + 1 > self.soft_week.get(teacher_id, 24):
            score += P_OVER_SOFT_WEEK

        # Even distribution: prefer days where this teacher is so far lighter.
        score += W_LIGHTER_DAY * day_load
        return score

    def _best_slot(self, req):
        """Return the highest-scoring valid single slot for a requirement, or None."""
        best = None
        best_score = None
        for slot in self.slots:
            if not self._can_place(req.teacher_id, req.batch_id, req.subject_id,
                                   slot.day, slot.period_num):
                continue
            s = self._score_slot(req.teacher_id, req.batch_id, req.subject_id,
                                 slot.day, slot.period_num)
            if best_score is None or s > best_score:
                best_score = s
                best = slot
        return best

    def _place_pinned(self, teachers):
        """Place admin-locked periods before anything else."""
        q = PinnedSlot.query
        if self.organization_id is not None:
            q = q.filter_by(organization_id=self.organization_id)
        for ps in q.all():
            day, period = ps.day, ps.period_number
            if (day, period) not in self.available:
                self.warnings.append(f"Pinned slot {day} P{period} is outside school hours (skipped)")
                continue
            if ps.batch_id not in self.batch_schedule:
                self.warnings.append(f"Pinned slot references unknown batch {ps.batch_id} (skipped)")
                continue

            subject_id = ps.subject_id
            teacher_id = ps.teacher_id
            if not teacher_id:
                eligible = [
                    t for t in teachers
                    if (subject_id, ps.batch_id) in self.teacher_can_teach.get(t.id, ())
                ]
                teacher_id = eligible[0].id if eligible else (teachers[0].id if teachers else None)
            if teacher_id is None:
                self.warnings.append(f"Pinned slot {day} P{period}: no teacher available (skipped)")
                continue

            # Track this subject for the batch even if it wasn't in batch.subject_ids.
            self.batch_schedule[ps.batch_id].setdefault(subject_id, 0)
            self.subject_periods.setdefault(subject_id, 1)
            self.subject_max_per_day.setdefault(subject_id, 1)

            if (day, period, ps.batch_id) in self.occupied or (teacher_id, day, period) in self.teacher_busy:
                self.warnings.append(f"Pinned slot {day} P{period} conflicts with another pin (skipped)")
                continue

            self._commit(teacher_id, subject_id, ps.batch_id, day, period)

    def _schedule_requirements(self, requirements: List[Requirement]):
        """Place each requirement's remaining periods (singles or doubles)."""
        for req in requirements:
            already = self.batch_schedule[req.batch_id].get(req.subject_id, 0)
            remaining = self.subject_periods.get(req.subject_id, req.periods) - already
            if remaining <= 0:
                continue
            if req.is_double and remaining >= 2:
                self._place_doubles(req, remaining)
            else:
                self._place_singles(req, remaining)

    def _place_singles(self, req: Requirement, remaining: int):
        """Place `remaining` single periods, each time picking the best-scoring slot.

        Re-evaluating after every placement lets the workload/preference score react
        to the slots already taken (consecutive runs, day load, etc.).
        """
        placed = 0
        for _ in range(remaining):
            slot = self._best_slot(req)
            if slot is None:
                break
            self._commit(req.teacher_id, req.subject_id, req.batch_id, slot.day, slot.period_num)
            placed += 1
        if placed < remaining:
            self.conflicts.append(
                f"Could only place {placed}/{remaining} periods of subject {req.subject_id} "
                f"for batch {req.batch_id}"
            )

    def _place_doubles(self, req: Requirement, remaining: int):
        """Place lab/double subjects as consecutive pairs (one block per day)."""
        pairs_needed = remaining // 2
        leftover_single = remaining % 2
        pairs_placed = 0

        for _ in range(pairs_needed):
            # Weekly quota must allow two more.
            if self.batch_schedule[req.batch_id].get(req.subject_id, 0) + 2 > self.subject_periods.get(req.subject_id, 1):
                break

            # Gather every feasible back-to-back pair and pick the best-scoring one.
            best_pair = None
            best_score = None
            for day in self.days_in_order:
                # One double block of a subject per day for a batch.
                if self.batch_day_subject.get((req.batch_id, day, req.subject_id), 0) > 0:
                    continue
                periods = self.slots_by_day.get(day, [])
                for i in range(len(periods) - 1):
                    p1, p2 = periods[i], periods[i + 1]
                    if p2 != p1 + 1:
                        continue  # must be back-to-back (no lunch gap between)
                    if (self._can_place(req.teacher_id, req.batch_id, req.subject_id, day, p1, check_spacing=False)
                            and self._can_place(req.teacher_id, req.batch_id, req.subject_id, day, p2, check_spacing=False)):
                        s = (self._score_slot(req.teacher_id, req.batch_id, req.subject_id, day, p1)
                             + self._score_slot(req.teacher_id, req.batch_id, req.subject_id, day, p2))
                        if best_score is None or s > best_score:
                            best_score = s
                            best_pair = (day, p1, p2)
            if best_pair is None:
                break
            day, p1, p2 = best_pair
            self._commit(req.teacher_id, req.subject_id, req.batch_id, day, p1)
            self._commit(req.teacher_id, req.subject_id, req.batch_id, day, p2)
            pairs_placed += 1

        if leftover_single:
            self._place_singles(req, 1)

        if pairs_placed < pairs_needed:
            self.conflicts.append(
                f"Could only place {pairs_placed}/{pairs_needed} double-period blocks of "
                f"subject {req.subject_id} for batch {req.batch_id}"
            )
    
    # ========================================================================
    # DATABASE SAVING
    # ========================================================================
    
    def _save_timetable(self, timetable_id: int, config: SchoolConfig):
        """Save generated timetable to database"""
        
        timetable = Timetable.query.get(timetable_id)
        if not timetable:
            timetable = Timetable(
                id=timetable_id,
                organization_id=self.organization_id,
                name=f"Generated Timetable {timetable_id}",
                status="draft",
                warnings=self.conflicts + self.warnings
            )
            db.session.add(timetable)
        else:
            # Clear existing slots
            TimetableSlot.query.filter_by(timetable_id=timetable_id).delete()
            # Keep the org tag in sync (e.g. timetable row pre-created elsewhere).
            if self.organization_id is not None:
                timetable.organization_id = self.organization_id
            timetable.warnings = self.conflicts + self.warnings
        
        # Save slots (timetable is keyed by (Period, batch_id)).
        for (slot, _batch_id), (teacher_id, subject_id, batch_id) in self.timetable.items():
            timetable_slot = TimetableSlot(
                organization_id=self.organization_id,
                timetable_id=timetable_id,
                day=slot.day,
                period_number=slot.period_num,
                batch_id=batch_id,
                teacher_id=teacher_id,
                subject_id=subject_id
            )
            db.session.add(timetable_slot)

        # Persist explicit LUNCH slots so the break is visible in grids/PDFs
        # (only for classes whose day is long enough to reach the lunch period).
        if getattr(self, "lunch_enabled", False) and getattr(self, "lunch_idx", None):
            from period_utils import working_days
            for day in working_days(config):
                for batch_id, limit in self.batch_periods.items():
                    if limit is not None and self.lunch_idx <= limit:
                        db.session.add(TimetableSlot(
                            organization_id=self.organization_id,
                            timetable_id=timetable_id,
                            day=day,
                            period_number=self.lunch_idx,
                            batch_id=batch_id,
                            is_lunch=True,
                        ))

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
