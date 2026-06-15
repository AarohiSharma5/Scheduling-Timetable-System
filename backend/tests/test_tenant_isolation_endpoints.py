"""HTTP-level cross-tenant isolation guards for the endpoints that previously
leaked across organizations.

Each test sets up two schools (the "victim" is created FIRST so it owns the
lowest ids), authenticates as the *attacker* school's admin, and asserts the
attacker cannot read or mutate the victim's data by guessing its record id.

Covers the IDOR fixes in:
  * GET/POST  /api/leaves/<id>            (read / approve / reject)
  * GET       /api/timetable/<id>/validate
  * GET       /api/timetable/<id>/conflicts/summary
  * GET       /api/timetable/<id>/conflicts/by-type
"""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_org_with_admin(db, *, slug, org_pw="OrgPass123", user_pw="UserPass123"):
    from models import Organization, User

    org = Organization(name=slug.title(), slug=slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()
    admin = User(name="Admin", email=f"admin@{slug}.test", role="admin",
                 organization_id=org.id, password_hash=generate_password_hash(user_pw),
                 must_change_password=False, status="active")
    db.session.add(admin)
    db.session.commit()
    return org, admin


def _login(app, slug, *, email=None, org_pw="OrgPass123", user_pw="UserPass123"):
    """Return a test client with an authenticated user session for `slug`."""
    client = app.test_client()
    r = client.post("/api/organizations/login",
                    json={"identifier": slug, "password": org_pw})
    assert r.status_code == 200, r.get_json()
    r = client.post("/api/auth/login",
                    json={"email": email or f"admin@{slug}.test", "password": user_pw})
    assert r.status_code == 200, r.get_json()
    return client


def _make_teacher(db, org_id, name="Victim Teacher"):
    from models import Teacher, User
    email = f"{name.replace(' ', '').lower()}@x.test"
    user = User(name=name, email=email, role="teacher",
                organization_id=org_id, password_hash="x")
    db.session.add(user)
    db.session.flush()
    t = Teacher(organization_id=org_id, user_id=user.id, name=name, email=email)
    db.session.add(t)
    db.session.commit()
    return t


def _make_leave(db, org_id, teacher_id):
    from models import LeaveRequest
    lr = LeaveRequest(organization_id=org_id, teacher_id=teacher_id,
                      leave_date=date(2026, 6, 15), reason="Flu", status="pending")
    db.session.add(lr)
    db.session.commit()
    return lr


def _make_timetable(db, org_id):
    from models import Timetable
    tt = Timetable(organization_id=org_id, name="Victim TT", status="draft")
    db.session.add(tt)
    db.session.commit()
    return tt


# --- Leave endpoints --------------------------------------------------------

def test_cannot_read_another_orgs_leave(app, db):
    victim, _ = _make_org_with_admin(db, slug="victim")
    _make_org_with_admin(db, slug="attacker")
    teacher = _make_teacher(db, victim.id)
    leave = _make_leave(db, victim.id, teacher.id)

    client = _login(app, "attacker")
    r = client.get(f"/api/leaves/{leave.id}")
    assert r.status_code == 404, "attacker must not read victim's leave"


def test_cannot_approve_another_orgs_leave(app, db):
    victim, _ = _make_org_with_admin(db, slug="victim")
    _make_org_with_admin(db, slug="attacker")
    teacher = _make_teacher(db, victim.id)
    leave = _make_leave(db, victim.id, teacher.id)

    client = _login(app, "attacker")
    r = client.post(f"/api/leaves/{leave.id}/approve", json={"auto_adjust": False})
    assert r.status_code == 404, "attacker must not approve victim's leave"

    from models import LeaveRequest
    assert LeaveRequest.query.get(leave.id).status == "pending", "status must be untouched"


def test_cannot_reject_another_orgs_leave(app, db):
    victim, _ = _make_org_with_admin(db, slug="victim")
    _make_org_with_admin(db, slug="attacker")
    teacher = _make_teacher(db, victim.id)
    leave = _make_leave(db, victim.id, teacher.id)

    client = _login(app, "attacker")
    r = client.post(f"/api/leaves/{leave.id}/reject", json={"rejection_reason": "no"})
    assert r.status_code == 404, "attacker must not reject victim's leave"

    from models import LeaveRequest
    assert LeaveRequest.query.get(leave.id).status == "pending", "status must be untouched"


def test_own_org_can_still_read_its_leave(app, db):
    """The guard must not break the legitimate same-org path."""
    org, _ = _make_org_with_admin(db, slug="solo")
    teacher = _make_teacher(db, org.id)
    leave = _make_leave(db, org.id, teacher.id)

    client = _login(app, "solo")
    r = client.get(f"/api/leaves/{leave.id}")
    assert r.status_code == 200
    assert r.get_json()["id"] == leave.id


# --- Timetable validation / conflict endpoints ------------------------------

def test_cannot_validate_another_orgs_timetable(app, db):
    victim, _ = _make_org_with_admin(db, slug="victim")
    _make_org_with_admin(db, slug="attacker")
    tt = _make_timetable(db, victim.id)

    client = _login(app, "attacker")
    for suffix in ("validate", "conflicts/summary", "conflicts/by-type"):
        r = client.get(f"/api/timetable/{tt.id}/{suffix}")
        assert r.status_code == 404, f"attacker must not access /{suffix} of victim's timetable"


def test_own_org_can_validate_its_timetable(app, db):
    org, _ = _make_org_with_admin(db, slug="solo")
    # The school config is required by the conflict detector.
    from models import SchoolConfig
    db.session.add(SchoolConfig(organization_id=org.id, periods_per_day=6, working_days=5))
    db.session.commit()
    tt = _make_timetable(db, org.id)

    client = _login(app, "solo")
    r = client.get(f"/api/timetable/{tt.id}/validate")
    assert r.status_code == 200
