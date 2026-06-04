"""Conflict-detector tests.

Prove the validation layer actually flags a teacher double-booking and stays
quiet on a clean timetable. Without this, "conflict-free" is just a claim.
"""

from conflict_detector import ConflictDetector


def _add_batch_and_slot(db, base, *, section, day, period):
    """Add a second batch + a slot taught by the SAME teacher at (day, period)."""
    from models import Batch, TimetableSlot

    org = base["org"]
    batch = Batch(
        organization_id=org.id, grade="9", section=section,
        student_count=30, subject_ids=[base["subject"].id],
    )
    db.session.add(batch)
    db.session.flush()

    slot = TimetableSlot(
        organization_id=org.id, timetable_id=base["timetable"].id, day=day,
        period_number=period, batch_id=batch.id, teacher_id=base["teacher"].id,
        subject_id=base["subject"].id,
    )
    db.session.add(slot)
    db.session.commit()
    return batch, slot


def test_detects_teacher_double_booking(db, make_school):
    base = make_school("Alpha", "alpha")
    # base already has one Monday/P1 slot for the teacher in section A.
    # Add section B with the same teacher ALSO at Monday/P1 => a clash.
    _add_batch_and_slot(db, base, section="B", day="Monday", period=1)

    report = ConflictDetector(base["timetable"].id).validate()

    assert report.is_valid is False
    error_types = {e["type"] for e in report.errors}
    assert "TEACHER_DOUBLE_BOOKING" in error_types


def test_clean_timetable_has_no_double_booking(db, make_school):
    base = make_school("Alpha", "alpha")
    # Same teacher, but the second class is at a DIFFERENT period => no clash.
    _add_batch_and_slot(db, base, section="B", day="Monday", period=2)

    report = ConflictDetector(base["timetable"].id).validate()

    error_types = {e["type"] for e in report.errors}
    assert "TEACHER_DOUBLE_BOOKING" not in error_types
