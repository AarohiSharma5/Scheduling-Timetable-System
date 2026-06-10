"""Tests for the capacity-aware block planner, feasibility audit and charge
rebalancing — the logic that fixes "periods don't match the timetable" and the
unhelpful "add more teachers" dead end.
"""

import pytest

import feasibility
from scheduler import SchedulingEngine


def _school(db, *, sections=2, subject_periods=5, teacher_caps=(5, 5), charges=None):
    """One grade with `sections` sections, one subject, len(teacher_caps) teachers.

    Every teacher is eligible for the subject in every section, so the planner
    must split the sections between them based on capacity.
    """
    from models import Organization, SchoolConfig, Subject, Batch, Teacher, User, Timetable

    org = Organization(name="Feas School", slug="feas", password_hash="x")
    db.session.add(org)
    db.session.flush()
    db.session.add(SchoolConfig(
        organization_id=org.id, start_time="08:00", end_time="14:00",
        period_duration=45, periods_per_day=8, working_days=5,
        has_lunch_break=False,
    ))

    math = Subject(organization_id=org.id, name="Mathematics", periods_per_week=subject_periods)
    db.session.add(math)
    db.session.flush()

    batches = []
    for i in range(sections):
        b = Batch(organization_id=org.id, grade="9", section=chr(ord("A") + i),
                  student_count=30, subject_ids=[math.id])
        db.session.add(b)
        batches.append(b)
    db.session.flush()
    batch_ids = [b.id for b in batches]

    teachers = []
    for i, cap in enumerate(teacher_caps):
        u = User(name=f"T{i + 1}", email=f"t{i + 1}@feas.test", role="teacher",
                 organization_id=org.id)
        db.session.add(u)
        db.session.flush()
        t = Teacher(
            organization_id=org.id, user_id=u.id, name=f"T{i + 1}",
            email=u.email, subject_ids=[math.id], assigned_batch_ids=batch_ids,
            max_periods_per_week=cap,
            charges=(charges or {}).get(i, []),
        )
        db.session.add(t)
        teachers.append(t)

    tt = Timetable(organization_id=org.id, name="Feas TT")
    db.session.add(tt)
    db.session.commit()
    return {"org": org, "subject": math, "batches": batches,
            "teachers": teachers, "timetable": tt}


def test_planner_splits_sections_instead_of_overloading_one_teacher(db):
    """2 sections x 5 periods, 2 teachers with capacity 5 each: each teacher
    must own exactly one section. The old greedy picker gave both sections to
    one teacher and reported a 5-period shortfall."""
    s = _school(db, sections=2, subject_periods=5, teacher_caps=(5, 5))
    ctx = feasibility.load_context(s["org"].id)
    plan = feasibility.plan_block_assignments(ctx)

    owners = set(plan["owner"].values())
    assert len(owners) == 2, "each section should go to a different teacher"
    assert plan["shortfalls"] == []
    assert all(p == 5 for p in plan["planned"].values())


def test_engine_schedules_completely_with_balanced_plan(db):
    """End to end: the engine must now produce a COMPLETE timetable for the
    same scenario that used to end in 'add more teachers'."""
    from models import TimetableSlot

    s = _school(db, sections=2, subject_periods=5, teacher_caps=(5, 5))
    engine = SchedulingEngine(organization_id=s["org"].id)
    success, _ = engine.generate_timetable(s["timetable"].id)

    assert success is True
    assert engine.report["complete"] is True, engine.report

    # Each section got its full 5 Maths periods.
    for b in s["batches"]:
        n = TimetableSlot.query.filter_by(
            timetable_id=s["timetable"].id, batch_id=b.id,
            subject_id=s["subject"].id).count()
        assert n == 5


def test_block_is_never_split_between_teachers(db):
    """Whole-section ownership: every period of (section, subject) has the
    same teacher, like real schools."""
    from models import TimetableSlot

    s = _school(db, sections=3, subject_periods=5, teacher_caps=(10, 10))
    engine = SchedulingEngine(organization_id=s["org"].id)
    engine.generate_timetable(s["timetable"].id)

    for b in s["batches"]:
        teacher_ids = {
            sl.teacher_id for sl in TimetableSlot.query.filter_by(
                timetable_id=s["timetable"].id, batch_id=b.id,
                subject_id=s["subject"].id).all()
        }
        assert len(teacher_ids) == 1, f"section {b.section} split across {teacher_ids}"


def test_audit_flags_class_over_budget(db):
    """A class whose subjects demand more periods than its week has must be
    flagged 'over' with the per-subject breakdown."""
    from models import Subject

    s = _school(db, sections=1, subject_periods=5, teacher_caps=(40,))
    org_id = s["org"].id
    # Add a giant second subject: 45/week demand vs 40 weekly slots.
    huge = Subject(organization_id=org_id, name="Everythingology",
                   periods_per_week=40, max_periods_per_day=8)
    db.session.add(huge)
    db.session.flush()
    b = s["batches"][0]
    b.subject_ids = list(b.subject_ids) + [huge.id]
    t = s["teachers"][0]
    t.subject_ids = list(t.subject_ids) + [huge.id]
    db.session.commit()

    report = feasibility.audit(org_id)
    cls = report["classes"][0]
    assert cls["status"] == "over"
    assert cls["demand"] == 45
    assert cls["demand"] > cls["budget"]
    assert report["ok"] is False


def test_audit_flags_impossible_daily_spread(db):
    """6 periods/week with max 1/day on a 5-day week can never fit."""
    s = _school(db, sections=1, subject_periods=6, teacher_caps=(40,))
    report = feasibility.audit(s["org"].id)
    cls = report["classes"][0]
    assert cls["impossible"], "spacing-impossible subject must be called out"
    assert "Mathematics" in cls["impossible"][0]


def test_charge_rebalance_suggested_and_applied(db):
    """Teacher A is short 3 periods because of a 3h Club charge; teacher B has
    spare capacity. The audit must suggest moving the charge, applying it must
    update both teachers, and the plan must then be deficit-free."""
    s = _school(
        db, sections=2, subject_periods=5,
        teacher_caps=(7, 20),
        charges={0: [{"charge_id": None, "name": "Club", "hours_per_week": 3}]},
    )
    org_id = s["org"].id
    t_a, t_b = s["teachers"]
    # Make B ineligible for Maths so all 10 Maths periods must go to A (cap 7).
    t_b.subject_ids = []
    t_b.assigned_batch_ids = []
    db.session.commit()

    report = feasibility.audit(org_id)
    assert report["summary"]["total_capacity_deficit"] == 3
    moves = report["rebalance_suggestions"]
    assert len(moves) == 1
    assert moves[0]["from_teacher_id"] == t_a.id
    assert moves[0]["to_teacher_id"] == t_b.id
    assert moves[0]["charge_name"] == "Club"
    assert moves[0]["hours"] == 3
    assert report["summary"]["rebalance_covers_deficit"] is True

    applied, errors = feasibility.apply_charge_moves(org_id, moves)
    assert errors == []
    assert len(applied) == 1

    db.session.refresh(t_a)
    db.session.refresh(t_b)
    assert t_a.charges == []
    assert t_a.max_periods_per_week == 10  # 7 + 3 freed
    assert any(c["name"] == "Club" for c in t_b.charges)
    assert t_b.max_periods_per_week == 17  # 20 - 3 taken on

    # After the move the plan has no deficit any more.
    after = feasibility.audit(org_id)
    assert after["summary"]["total_capacity_deficit"] == 0


def test_class_teacher_charge_is_never_moved(db):
    """Class-teachership hours stay with the class teacher no matter the deficit."""
    s = _school(
        db, sections=2, subject_periods=5,
        teacher_caps=(7, 20),
        charges={0: [{"charge_id": None, "name": "Class Teacher", "hours_per_week": 5}]},
    )
    t_a, t_b = s["teachers"]
    t_a.is_class_teacher = True
    t_a.class_teacher_batch_id = s["batches"][0].id
    t_b.subject_ids = []
    t_b.assigned_batch_ids = []
    db.session.commit()

    report = feasibility.audit(s["org"].id)
    assert report["summary"]["total_capacity_deficit"] > 0
    assert report["rebalance_suggestions"] == [], "CT duty must never be suggested for a move"

    applied, errors = feasibility.apply_charge_moves(s["org"].id, [{
        "from_teacher_id": t_a.id, "to_teacher_id": t_b.id,
        "charge_name": "Class Teacher", "hours": 5,
    }])
    assert applied == []
    assert errors and "never moved" in errors[0]


def test_unstaffed_subject_reported(db):
    """A subject nobody can teach is reported as unstaffed, not silently dropped."""
    s = _school(db, sections=1, subject_periods=5, teacher_caps=(10,))
    t = s["teachers"][0]
    t.subject_ids = []
    t.assigned_batch_ids = []
    db.session.commit()

    report = feasibility.audit(s["org"].id)
    subj = next(x for x in report["subjects"] if x["subject"] == "Mathematics")
    assert subj["status"] == "unstaffed"
    assert subj["unstaffed_sections"] == ["Grade 9-A"]
