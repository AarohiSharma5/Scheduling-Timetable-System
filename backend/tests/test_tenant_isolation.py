"""Cross-tenant isolation guards.

These tests fail loudly if a query ever crosses organization boundaries. They
deliberately create the "other" school FIRST (so it owns the lowest id and is
what an unscoped ``.query.first()`` would return), then assert that operations
on the second school never surface the first school's data.

This is the regression net for the multi-tenant leaks fixed in
``format_timetable_as_plan``, ``ConflictDetector._load_data`` and friends.
"""

from routes import format_timetable_as_plan
from conflict_detector import ConflictDetector


def test_format_timetable_as_plan_uses_own_org_config(make_school):
    # Beta created first => lowest id => what an unscoped .first() would return.
    beta = make_school("Beta School", "beta", periods_per_day=4, working_days=4)
    alpha = make_school("Alpha School", "alpha", periods_per_day=8, working_days=6)

    plan = format_timetable_as_plan(alpha["timetable"])
    profile = plan["school_profile"]

    # Must reflect Alpha's own config/identity, never Beta's.
    assert profile["institution_name"] == "Alpha School"
    assert profile["periods_per_day"] == 8
    assert profile["days_per_week"] == 6


def test_plan_teachers_and_subjects_are_tenant_scoped(make_school):
    beta = make_school("Beta School", "beta", periods_per_day=4)
    alpha = make_school("Alpha School", "alpha", periods_per_day=8)

    plan = format_timetable_as_plan(alpha["timetable"])

    teacher_names = {t["name"] for t in plan["teachers"]}
    subject_names = {s["name"] for s in plan["subjects"]}

    assert teacher_names == {"Alpha School Teacher"}
    assert "Beta School Teacher" not in teacher_names
    assert subject_names == {"Alpha School Math"}
    assert "Beta School Math" not in subject_names


def test_conflict_detector_loads_own_org_config(make_school):
    beta = make_school("Beta School", "beta", periods_per_day=4)
    alpha = make_school("Alpha School", "alpha", periods_per_day=8)

    detector = ConflictDetector(alpha["timetable"].id)
    detector._load_data()

    assert detector.config.organization_id == alpha["org"].id
    assert detector.config.periods_per_day == 8


def test_each_school_plan_is_independent(make_school):
    """Sanity: both schools resolve to their own identity, not a shared first()."""
    beta = make_school("Beta School", "beta", periods_per_day=4, working_days=4)
    alpha = make_school("Alpha School", "alpha", periods_per_day=8, working_days=6)

    beta_plan = format_timetable_as_plan(beta["timetable"])
    alpha_plan = format_timetable_as_plan(alpha["timetable"])

    assert beta_plan["school_profile"]["institution_name"] == "Beta School"
    assert beta_plan["school_profile"]["periods_per_day"] == 4
    assert alpha_plan["school_profile"]["institution_name"] == "Alpha School"
    assert alpha_plan["school_profile"]["periods_per_day"] == 8
