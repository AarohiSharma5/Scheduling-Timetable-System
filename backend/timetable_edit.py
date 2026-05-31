"""Validation + helpers for manual timetable editing.

A "slot" here is any object/dict exposing: day, period_number, batch_id,
teacher_id, subject_id, room, is_lunch. We validate a *whole proposed grid*
(cheap even for thousands of slots) so the same code covers single-cell edits,
swaps, and full-version saves.

Hard conflicts that block a save:
  * teacher_double_book  - one teacher in two batches at the same day/period
  * section_conflict     - one batch with two subjects at the same day/period
  * room_conflict        - one room used by two batches at the same day/period (labs)
  * teacher_unavailable  - teacher placed in a slot they declared unavailable/blocked
"""

from collections import defaultdict


def _slot_get(slot, key, default=None):
    """Read a field from either a dict or a model instance."""
    if isinstance(slot, dict):
        return slot.get(key, default)
    return getattr(slot, key, default)


def _norm_unavail(entries):
    """Normalize a teacher's unavailable/blocked list to a set of (day, period)."""
    out = set()
    for e in entries or []:
        try:
            day = e.get("day")
            period = e.get("period", e.get("period_number"))
            if day is not None and period is not None:
                out.add((str(day), int(period)))
        except (AttributeError, TypeError, ValueError):
            continue
    return out


def build_teacher_unavailable(teachers, preferences):
    """Map teacher_id -> set of (day, period) they cannot teach.

    Merges Teacher.unavailable_slots with TeacherPreference.blocked_slots.
    """
    unavail = defaultdict(set)
    for t in teachers:
        unavail[t.id] |= _norm_unavail(getattr(t, "unavailable_slots", None))
    for p in preferences:
        unavail[p.teacher_id] |= _norm_unavail(getattr(p, "blocked_slots", None))
    return unavail


def collect_conflicts(slots, teacher_unavailable=None, teacher_names=None,
                      subject_names=None, batch_names=None):
    """Return a list of hard-conflict dicts for a proposed set of slots."""
    teacher_unavailable = teacher_unavailable or {}
    teacher_names = teacher_names or {}
    subject_names = subject_names or {}
    batch_names = batch_names or {}

    by_teacher_slot = defaultdict(set)   # (teacher, day, period) -> {batch}
    by_section_slot = defaultdict(list)  # (batch, day, period) -> [subject]
    by_room_slot = defaultdict(set)      # (room, day, period) -> {batch}
    conflicts = []

    def label_teacher(tid):
        return teacher_names.get(tid, f"Teacher #{tid}")

    def label_batch(bid):
        return batch_names.get(bid, f"Class #{bid}")

    for s in slots:
        if _slot_get(s, "is_lunch"):
            continue
        day = _slot_get(s, "day")
        period = _slot_get(s, "period_number")
        batch = _slot_get(s, "batch_id")
        teacher = _slot_get(s, "teacher_id")
        subject = _slot_get(s, "subject_id")
        room = _slot_get(s, "room")
        if subject is None and teacher is None:
            continue  # genuinely empty cell

        if teacher is not None:
            by_teacher_slot[(teacher, day, period)].add(batch)
            if (str(day), int(period)) in teacher_unavailable.get(teacher, set()):
                conflicts.append({
                    "type": "teacher_unavailable",
                    "day": day, "period": period,
                    "batch_id": batch, "teacher_id": teacher,
                    "message": f"{label_teacher(teacher)} is unavailable on {day} P{period}.",
                })
        if batch is not None:
            by_section_slot[(batch, day, period)].append(subject)
        if room:
            by_room_slot[(str(room).strip().lower(), day, period)].add((batch, room))

    for (teacher, day, period), batches in by_teacher_slot.items():
        if len(batches) > 1:
            conflicts.append({
                "type": "teacher_double_book",
                "day": day, "period": period, "teacher_id": teacher,
                "batch_ids": sorted(b for b in batches if b is not None),
                "message": (f"{label_teacher(teacher)} is double-booked on {day} P{period} "
                            f"({', '.join(label_batch(b) for b in batches)})."),
            })

    for (batch, day, period), subjects in by_section_slot.items():
        if len(subjects) > 1:
            conflicts.append({
                "type": "section_conflict",
                "day": day, "period": period, "batch_id": batch,
                "message": f"{label_batch(batch)} has two subjects on {day} P{period}.",
            })

    for (_, day, period), entries in by_room_slot.items():
        batches = {b for (b, _r) in entries}
        if len(batches) > 1:
            room = next(iter(entries))[1]
            conflicts.append({
                "type": "room_conflict",
                "day": day, "period": period, "room": room,
                "batch_ids": sorted(b for b in batches if b is not None),
                "message": f"Room '{room}' is double-booked on {day} P{period}.",
            })

    return conflicts
