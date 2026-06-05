"""Tests for operational features: async-style generation jobs, health, pagination."""

from datetime import date

from werkzeug.security import generate_password_hash


def _generatable_school(db, *, slug, org_pw="OrgPass123", admin_pw="AdminPass1"):
    """A minimal but schedulable school with a login-able admin."""
    from models import Organization, SchoolConfig, Subject, Batch, Teacher, User

    org = Organization(name=slug.title(), slug=slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()
    admin = User(name="Admin", email=f"admin@{slug}.test", role="admin",
                 organization_id=org.id, password_hash=generate_password_hash(admin_pw))
    db.session.add(admin)
    db.session.add(SchoolConfig(organization_id=org.id, periods_per_day=6,
                                working_days=5, has_lunch_break=False))
    math = Subject(organization_id=org.id, name="Math", periods_per_week=5)
    eng = Subject(organization_id=org.id, name="English", periods_per_week=5)
    db.session.add_all([math, eng])
    db.session.flush()

    batch_ids = []
    for section in ("A", "B"):
        b = Batch(organization_id=org.id, grade="9", section=section,
                  student_count=30, subject_ids=[math.id, eng.id])
        db.session.add(b)
        db.session.flush()
        batch_ids.append(b.id)

    for name, subj in (("MathT", math), ("EngT", eng)):
        u = User(name=name, email=f"{name.lower()}@{slug}.test", role="teacher",
                 organization_id=org.id)
        db.session.add(u)
        db.session.flush()
        db.session.add(Teacher(organization_id=org.id, user_id=u.id, name=name,
                               email=u.email, subject_ids=[subj.id],
                               assigned_batch_ids=batch_ids, max_periods_per_week=30))
    db.session.commit()
    return {"org": org, "admin": admin, "org_pw": org_pw, "admin_pw": admin_pw}


def _admin_client(app, s):
    c = app.test_client()
    assert c.post("/api/organizations/login",
                  json={"identifier": s["org"].slug, "password": s["org_pw"]}).status_code == 200
    assert c.post("/api/auth/login",
                  json={"email": s["admin"].email, "password": s["admin_pw"]}).status_code == 200
    return c


# --------------------------------------------------------------------------- health

def test_health_live_has_no_dependencies(app, db):
    c = app.test_client()
    r = c.get("/api/health/live")
    assert r.status_code == 200 and r.get_json()["status"] == "alive"


def test_health_ready_reports_database_ok(app, db):
    c = app.test_client()
    r = c.get("/api/health/ready")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"


# --------------------------------------------------------------------------- generation jobs

def test_generate_creates_job_and_runs_sync_fallback(app, db):
    """Without Redis/worker, generate runs inline and records a completed job."""
    from models import GenerationJob, TimetableSlot

    s = _generatable_school(db, slug="genco")
    admin = _admin_client(app, s)

    r = admin.post("/api/timetable/generate", json={"name": "Term 1 TT"})
    # Sync fallback returns the full result with 201 and a job_id.
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["success"] is True
    assert "job_id" in body
    assert body["slots_generated"] > 0

    job = GenerationJob.query.get(body["job_id"])
    assert job is not None
    assert job.status == "completed"
    assert job.result["slots_generated"] == body["slots_generated"]
    assert TimetableSlot.query.filter_by(timetable_id=job.timetable_id).count() > 0


def test_generation_job_status_endpoint(app, db):
    s = _generatable_school(db, slug="genstat")
    admin = _admin_client(app, s)
    body = admin.post("/api/timetable/generate", json={"name": "TT"}).get_json()

    r = admin.get(f"/api/timetable/jobs/{body['job_id']}")
    assert r.status_code == 200
    job = r.get_json()
    assert job["job_id"] == body["job_id"]
    assert job["status"] == "completed"
    assert job["result"]["success"] is True


def test_generation_job_is_tenant_scoped(app, db):
    a = _generatable_school(db, slug="genta")
    b = _generatable_school(db, slug="gentb")
    ca = _admin_client(app, a)
    body = ca.post("/api/timetable/generate", json={"name": "A"}).get_json()
    # Org B cannot read org A's job.
    cb = _admin_client(app, b)
    assert cb.get(f"/api/timetable/jobs/{body['job_id']}").status_code == 404


# --------------------------------------------------------------------------- pagination

def _make_students(db, org_id, n):
    from models import Student
    for i in range(n):
        db.session.add(Student(
            organization_id=org_id, student_id=f"S{org_id}_{i}",
            admission_no=f"A{org_id}_{i}", first_name=f"Stu{i:02d}", last_name="X",
            class_grade="9", section="A", roll_no=i + 1,
            admission_date=date(2024, 4, 1), status="Active"))
    db.session.commit()


def test_students_default_returns_array(app, db):
    s = _generatable_school(db, slug="pag1")
    _make_students(db, s["org"].id, 5)
    admin = _admin_client(app, s)
    data = admin.get("/api/admin/students").get_json()
    assert isinstance(data, list)
    assert len(data) == 5


def test_students_pagination_envelope(app, db):
    s = _generatable_school(db, slug="pag2")
    _make_students(db, s["org"].id, 25)
    admin = _admin_client(app, s)
    r = admin.get("/api/admin/students?page=1&per_page=10")
    assert r.status_code == 200
    body = r.get_json()
    assert body["total"] == 25
    assert body["pages"] == 3
    assert len(body["data"]) == 10
    page3 = admin.get("/api/admin/students?page=3&per_page=10").get_json()
    assert len(page3["data"]) == 5


def test_students_search_filters_in_sql(app, db):
    s = _generatable_school(db, slug="pag3")
    _make_students(db, s["org"].id, 10)
    admin = _admin_client(app, s)
    data = admin.get("/api/admin/students?q=stu03").get_json()
    assert len(data) == 1
    assert data[0]["first_name"] == "Stu03"
