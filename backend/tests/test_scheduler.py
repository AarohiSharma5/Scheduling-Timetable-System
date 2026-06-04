"""Scheduler correctness tests.

The product's central promise is a clash-free timetable. These tests build a
small but realistic school, run the real scheduling engine, and assert the
hard invariants on whatever it produces:

  * no teacher is in two places at once (teacher double-booking)
  * no class has two subjects at once (batch overlap)
  * a teacher is only scheduled for a batch they're assigned to

If a future change breaks any of these, CI goes red.
"""

import pytest

from scheduler import SchedulingEngine


@pytest.fixture()
def small_school(db):
    """Org with 2 batches, 2 subjects, 2 teachers (each covers both batches)."""
    from models import (
        Organization, SchoolConfig, Subject, Batch, Teacher, User, Timetable,
    )

    org = Organization(name="Engine School", slug="engine", password_hash="x")
    db.session.add(org)
    db.session.flush()

    db.session.add(SchoolConfig(
        organization_id=org.id, periods_per_day=6, working_days=5,
        has_lunch_break=False,
    ))

    math = Subject(organization_id=org.id, name="Math", periods_per_week=5)
    eng = Subject(organization_id=org.id, name="English", periods_per_week=5)
    db.session.add_all([math, eng])
    db.session.flush()

    batches = []
    for section in ("A", "B"):
        b = Batch(
            organization_id=org.id, grade="9", section=section,
            student_count=30, subject_ids=[math.id, eng.id],
        )
        db.session.add(b)
        batches.append(b)
    db.session.flush()
    batch_ids = [b.id for b in batches]

    def make_teacher(name, subject):
        user = User(name=name, email=f"{name.lower()}@engine.test",
                    role="teacher", organization_id=org.id)
        db.session.add(user)
        db.session.flush()
        t = Teacher(
            organization_id=org.id, user_id=user.id, name=name,
            email=user.email, subject_ids=[subject.id],
            assigned_batch_ids=batch_ids, max_periods_per_week=30,
        )
        db.session.add(t)
        db.session.flush()
        return t

    t_math = make_teacher("MathTeacher", math)
    t_eng = make_teacher("EngTeacher", eng)

    timetable = Timetable(organization_id=org.id, name="Engine TT")
    db.session.add(timetable)
    db.session.commit()

    return {
        "org": org, "timetable": timetable, "batch_ids": batch_ids,
        "teachers": {t_math.id: batch_ids, t_eng.id: batch_ids},
    }


def _saved_slots(db, timetable_id):
    from models import TimetableSlot
    return TimetableSlot.query.filter_by(timetable_id=timetable_id).all()


def test_generation_succeeds_and_creates_slots(db, small_school):
    engine = SchedulingEngine(organization_id=small_school["org"].id)
    success, _warnings = engine.generate_timetable(small_school["timetable"].id)

    assert success is True
    slots = _saved_slots(db, small_school["timetable"].id)
    assert len(slots) > 0


def test_no_teacher_double_booking(db, small_school):
    engine = SchedulingEngine(organization_id=small_school["org"].id)
    engine.generate_timetable(small_school["timetable"].id)

    seen = set()  # (teacher_id, day, period) must be unique
    for s in _saved_slots(db, small_school["timetable"].id):
        if not s.teacher_id or s.is_lunch:
            continue
        key = (s.teacher_id, s.day, s.period_number)
        assert key not in seen, f"Teacher {s.teacher_id} double-booked at {s.day} P{s.period_number}"
        seen.add(key)


def test_no_batch_overlap(db, small_school):
    engine = SchedulingEngine(organization_id=small_school["org"].id)
    engine.generate_timetable(small_school["timetable"].id)

    seen = set()  # (batch_id, day, period) must be unique
    for s in _saved_slots(db, small_school["timetable"].id):
        if not s.batch_id:
            continue
        key = (s.batch_id, s.day, s.period_number)
        assert key not in seen, f"Batch {s.batch_id} has two classes at {s.day} P{s.period_number}"
        seen.add(key)


def test_teacher_only_teaches_assigned_batches(db, small_school):
    engine = SchedulingEngine(organization_id=small_school["org"].id)
    engine.generate_timetable(small_school["timetable"].id)

    allowed = small_school["teachers"]
    for s in _saved_slots(db, small_school["timetable"].id):
        if not s.teacher_id or not s.batch_id or s.is_lunch:
            continue
        if s.teacher_id in allowed:
            assert s.batch_id in allowed[s.teacher_id]
