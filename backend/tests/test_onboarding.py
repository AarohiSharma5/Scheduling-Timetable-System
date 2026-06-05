"""Tests for the setup checklist (onboarding) and removal of the dead coordinator role."""

from werkzeug.security import generate_password_hash


def _school(db, *, slug, org_pw="OrgPass123", admin_pw="AdminPass1"):
    from models import Organization, User
    org = Organization(name=slug.title(), slug=slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()
    admin = User(name="Admin", email=f"admin@{slug}.test", role="admin",
                 organization_id=org.id, password_hash=generate_password_hash(admin_pw))
    db.session.add(admin)
    db.session.commit()
    return {"org": org, "admin": admin, "org_pw": org_pw, "admin_pw": admin_pw}


def _admin_client(app, s):
    c = app.test_client()
    assert c.post("/api/organizations/login",
                  json={"identifier": s["org"].slug, "password": s["org_pw"]}).status_code == 200
    assert c.post("/api/auth/login",
                  json={"email": s["admin"].email, "password": s["admin_pw"]}).status_code == 200
    return c


def test_onboarding_status_for_empty_school(app, db):
    s = _school(db, slug="onbempty")
    admin = _admin_client(app, s)
    r = admin.get("/api/admin/onboarding")
    assert r.status_code == 200
    body = r.get_json()
    assert body["completed"] is False
    assert body["total"] == 6
    # Nothing created yet, so every action step is undone.
    keys = {step["key"]: step["done"] for step in body["steps"]}
    assert keys["subjects"] is False
    assert keys["students"] is False
    assert keys["timetable"] is False


def test_onboarding_reflects_created_entities(app, db):
    from models import Subject, Batch
    s = _school(db, slug="onbprog")
    db.session.add(Subject(organization_id=s["org"].id, name="Math", periods_per_week=5))
    db.session.add(Batch(organization_id=s["org"].id, grade="9", section="A", student_count=0))
    db.session.commit()

    admin = _admin_client(app, s)
    body = admin.get("/api/admin/onboarding").get_json()
    keys = {step["key"]: step["done"] for step in body["steps"]}
    assert keys["subjects"] is True
    assert keys["batches"] is True
    assert keys["teachers"] is False


def test_onboarding_dismiss(app, db):
    s = _school(db, slug="onbdismiss")
    admin = _admin_client(app, s)
    assert admin.post("/api/admin/onboarding/dismiss").status_code == 200
    body = admin.get("/api/admin/onboarding").get_json()
    assert body["completed"] is True


def test_onboarding_is_tenant_scoped(app, db):
    from models import Subject
    a = _school(db, slug="onbta")
    db.session.add(Subject(organization_id=a["org"].id, name="Math", periods_per_week=5))
    db.session.commit()
    b = _school(db, slug="onbtb")

    # Org B's checklist must not see org A's subject.
    cb = _admin_client(app, b)
    body = cb.get("/api/admin/onboarding").get_json()
    keys = {step["key"]: step["done"] for step in body["steps"]}
    assert keys["subjects"] is False


def test_coordinator_role_cannot_be_invited(app, db):
    s = _school(db, slug="nocoord")
    admin = _admin_client(app, s)
    r = admin.post("/api/invitations",
                   json={"email": "x@nocoord.test", "name": "X", "role": "coordinator"})
    assert r.status_code == 400
    assert "coordinator" in (r.get_json().get("error") or "").lower()


def test_teacher_role_still_invitable(app, db):
    s = _school(db, slug="okteacher")
    admin = _admin_client(app, s)
    r = admin.post("/api/invitations",
                   json={"email": "t@okteacher.test", "name": "T", "role": "teacher"})
    assert r.status_code in (200, 201), r.get_json()
