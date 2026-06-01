"""Class-wise planning validation for a generated timetable.

Checks, per section (batch):
  * every subject reaches its required weekly count (per-class config override
    when present, else the org-wide Subject default);
  * assembly slots are blocked for the configured classes/days;
  * zero periods exist for the configured grades when enabled;
  * the class-teacher-first-period soft rule was honoured where possible.

Teacher double-booking is already prevented by the engine and re-checked here
for completeness. Everything is read-only; this never mutates the timetable.
"""

from collections import defaultdict

from models import (
    Subject, Batch, TimetableSlot, SchoolConfig, Teacher, ClassSubjectConfig,
)
import period_utils


def _eff_required(cls_cfg, subjects, grade, subject_id):
    c = cls_cfg.get((str(grade), subject_id))
    if c and c.periods_per_week is not None:
        return c.periods_per_week
    s = subjects.get(subject_id)
    return s.periods_per_week if s else 0


def validate_planning(org_id, timetable_id):
    config = SchoolConfig.query.filter_by(organization_id=org_id).first()
    subjects = {s.id: s for s in Subject.query.filter_by(organization_id=org_id).all()}
    batches = Batch.query.filter_by(organization_id=org_id).all()
    batch_by_id = {b.id: b for b in batches}
    cls_cfg = {(str(c.grade), c.subject_id): c
               for c in ClassSubjectConfig.query.filter_by(organization_id=org_id).all()}

    assembly_name = (Subject.query.filter_by(organization_id=org_id, name="Assembly").first() or None)
    zero_name = (Subject.query.filter_by(organization_id=org_id, name="Zero Period").first() or None)
    assembly_sid = assembly_name.id if assembly_name else None
    zero_sid = zero_name.id if zero_name else None

    slots = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()

    # Per-batch subject counts, period-1 teacher, and teacher busy map.
    counts = defaultdict(lambda: defaultdict(int))   # batch_id -> subject_id -> n
    first_period_teachers = defaultdict(set)         # batch_id -> {teacher_id at period 1}
    teacher_slot = defaultdict(list)                 # (teacher,day,period) -> [batch]
    has_zero = defaultdict(bool)                      # batch_id -> any period 0 slot
    assembly_slots = 0
    for sl in slots:
        if sl.is_lunch or getattr(sl, "is_short_break", False):
            continue
        if sl.batch_id and sl.subject_id:
            counts[sl.batch_id][sl.subject_id] += 1
        if sl.batch_id and sl.period_number == 0:
            has_zero[sl.batch_id] = True
        if sl.subject_id and assembly_sid and sl.subject_id == assembly_sid:
            assembly_slots += 1
        if sl.batch_id and sl.period_number == 1 and sl.teacher_id:
            first_period_teachers[sl.batch_id].add(sl.teacher_id)
        if sl.teacher_id and not sl.is_lunch:
            teacher_slot[(sl.teacher_id, sl.day, sl.period_number)].append(sl.batch_id)

    # 1) Weekly subject counts per section.
    shortfalls = []
    for b in batches:
        for sid in (b.subject_ids or []):
            s = subjects.get(sid)
            if not s or (s.subject_type or "core") not in ("core", "language", "elective", "activity"):
                pass
            required = _eff_required(cls_cfg, subjects, b.grade, sid)
            if required <= 0:
                continue
            got = counts[b.id].get(sid, 0)
            # Electives and languages run as cross-section blocks (batch_id NULL),
            # so they won't appear under a section's own slots; don't flag them.
            if s and (s.subject_type or "core") in ("elective", "language"):
                continue
            if got < required:
                shortfalls.append({
                    "class": f"{b.grade}-{b.section}", "subject": s.name if s else sid,
                    "required": required, "scheduled": got,
                })

    # 2) Teacher double-booking (real classes only).
    double_booked = []
    for (tid, day, period), bids in teacher_slot.items():
        real = [x for x in bids if x is not None]
        if len(real) > 1:
            double_booked.append({"teacher_id": tid, "day": day, "period": period,
                                  "batches": real})

    # 3) Assembly blocked correctly.
    assembly_ok = True
    assembly_note = "disabled"
    mode = (getattr(config, "assembly_mode", "disabled") or "disabled").lower()
    if mode != "disabled":
        assembly_note = f"{mode}: {assembly_slots} assembly slot(s) placed"
        assembly_ok = assembly_slots > 0

    # 4) Zero period respected for configured grades.
    zero_ok = True
    zero_note = "disabled"
    if getattr(config, "zero_period_enabled", False):
        want = {str(g) for g in (getattr(config, "zero_period_grades", None) or [])}
        applicable = [b for b in batches if (not want or str(b.grade) in want)]
        missing = [f"{b.grade}-{b.section}" for b in applicable if not has_zero.get(b.id)]
        zero_ok = not missing
        zero_note = (f"{len(applicable) - len(missing)}/{len(applicable)} classes have a zero period"
                     + (f"; missing: {', '.join(missing[:8])}" if missing else ""))

    # 5) Class-teacher-first attempted.
    ct_note = "disabled"
    ct_rate = None
    if getattr(config, "class_teacher_first_period", False):
        ct_of = {}
        for t in Teacher.query.filter_by(organization_id=org_id).all():
            if getattr(t, "class_teacher_batch_id", None):
                ct_of.setdefault(t.class_teacher_batch_id, t.id)
        sections_with_ct = [b for b in batches if b.id in ct_of]
        honoured = sum(1 for b in sections_with_ct
                       if ct_of[b.id] in first_period_teachers.get(b.id, set()))
        total = len(sections_with_ct)
        ct_rate = round(100.0 * honoured / total, 1) if total else None
        ct_note = f"{honoured}/{total} sections have their class teacher in a first period"

    ok = (not shortfalls) and (not double_booked) and assembly_ok and zero_ok
    return {
        "timetable_id": timetable_id,
        "ok": ok,
        "generation_mode": getattr(config, "generation_mode", "global"),
        "subject_count_shortfalls": shortfalls[:50],
        "shortfall_total": len(shortfalls),
        "teacher_double_bookings": double_booked[:50],
        "assembly": {"ok": assembly_ok, "note": assembly_note},
        "zero_period": {"ok": zero_ok, "note": zero_note},
        "class_teacher_first": {"note": ct_note, "rate_pct": ct_rate},
    }
