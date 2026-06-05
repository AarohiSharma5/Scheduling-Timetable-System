"""Homework / assignments tests (HTTP layer, real auth + tenant scoping)."""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_school(db, *, slug, org_pw="OrgPass123", admin_pw="AdminPass1"):
    from models import Organization, User, Batch, Student, Subject, Teacher

    org = Organization(name=slug.title(), slug=slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()
    admin = User(name="Admin", email=f"admin@{slug}.test", role="admin",
                 organization_id=org.id, password_hash=generate_password_hash(admin_pw))
    db.session.add(admin)
    subject = Subject(organization_id=org.id, name="Math", periods_per_week=5)
    db.session.add(subject)
    batch = Batch(organization_id=org.id, grade="9", section="A", subject_ids=[])
    db.session.add(batch)
    db.session.flush()
    batch.subject_ids = [subject.id]

    stu_user = User(name="Kid", email=f"kid@{slug}.test", role="student",
                    organization_id=org.id, password_hash=generate_password_hash("KidPass123"))
    db.session.add(stu_user)
    db.session.flush()
    student = Student(organization_id=org.id, student_id=f"{slug.upper()}STU1",
                      admission_no=f"{slug.upper()}ADM1", first_name="Kid", last_name="One",
                      class_grade="9", section="A", roll_no=1, admission_date=date(2024, 4, 1),
                      status="Active", user_id=stu_user.id)
    db.session.add(student)

    other = Batch(organization_id=org.id, grade="9", section="B", subject_ids=[])
    db.session.add(other)
    db.session.flush()
    t_user = User(name="Teach", email=f"teach@{slug}.test", role="teacher",
                  organization_id=org.id, password_hash=generate_password_hash("TeachPass1"))
    db.session.add(t_user)
    db.session.flush()
    db.session.add(Teacher(organization_id=org.id, user_id=t_user.id, name="Teach",
                           email=f"teach@{slug}.test", assigned_batch_ids=[batch.id]))
    db.session.commit()
    return {"org": org, "admin": admin, "subject": subject, "batch": batch,
            "other_batch": other, "student": student, "student_user": stu_user,
            "teacher_user": t_user, "org_pw": org_pw, "admin_pw": admin_pw}


def _client(app, slug, email, org_pw, user_pw):
    c = app.test_client()
    assert c.post("/api/organizations/login",
                  json={"identifier": slug, "password": org_pw}).status_code == 200
    assert c.post("/api/auth/login", json={"email": email, "password": user_pw}).status_code == 200
    return c


def _admin(app, s):
    return _client(app, s["org"].slug, s["admin"].email, s["org_pw"], s["admin_pw"])


def _teacher(app, s):
    return _client(app, s["org"].slug, s["teacher_user"].email, s["org_pw"], "TeachPass1")


def _student(app, s):
    return _client(app, s["org"].slug, s["student_user"].email, s["org_pw"], "KidPass123")


def test_teacher_creates_for_own_class_only(app, db):
    s = _make_school(db, slug="alpha")
    teacher = _teacher(app, s)
    ok = teacher.post("/api/assignments", json={
        "title": "Algebra", "batch_id": s["batch"].id, "subject_id": s["subject"].id,
        "due_date": "2026-07-01"})
    assert ok.status_code == 201

    bad = teacher.post("/api/assignments", json={
        "title": "No", "batch_id": s["other_batch"].id})
    assert bad.status_code == 403


def test_student_sees_and_submits(app, db):
    s = _make_school(db, slug="beta")
    admin = _admin(app, s)
    a = admin.post("/api/assignments", json={
        "title": "Essay", "batch_id": s["batch"].id}).get_json()

    student = _student(app, s)
    listing = student.get("/api/assignments").get_json()
    assert len(listing) == 1
    assert listing[0]["my_status"] == "pending"

    r = student.post(f"/api/assignments/{a['id']}/submit", json={"note": "done"})
    assert r.status_code == 200 and r.get_json()["status"] == "submitted"
    # Idempotent.
    student.post(f"/api/assignments/{a['id']}/submit", json={"note": "again"})
    from models import AssignmentSubmission
    assert AssignmentSubmission.query.filter_by(assignment_id=a["id"]).count() == 1


def test_teacher_grades_submission(app, db):
    s = _make_school(db, slug="gamma")
    admin = _admin(app, s)
    a = admin.post("/api/assignments", json={"title": "HW", "batch_id": s["batch"].id}).get_json()
    _student(app, s).post(f"/api/assignments/{a['id']}/submit", json={})

    teacher = _teacher(app, s)
    subs = teacher.get(f"/api/assignments/{a['id']}/submissions").get_json()
    assert subs["students"][0]["status"] == "submitted"

    r = teacher.put(f"/api/assignments/{a['id']}/submissions/{s['student'].id}",
                    json={"grade": "A", "feedback": "Great"})
    assert r.status_code == 200 and r.get_json()["status"] == "graded"


def test_parent_views_childs_homework(app, db):
    s = _make_school(db, slug="delta")
    admin = _admin(app, s)
    admin.post("/api/assignments", json={"title": "Read ch.1", "batch_id": s["batch"].id})
    created = admin.post("/api/admin/parents", json={
        "name": "P", "email": "p@delta.test", "student_ids": [s["student"].id]}).get_json()
    parent = _client(app, "delta", "p@delta.test", s["org_pw"],
                     created["credentials"]["temporary_password"])
    res = parent.get(f"/api/assignments/student/{s['student'].id}")
    assert res.status_code == 200
    assert len(res.get_json()["assignments"]) == 1


def test_homework_tenant_isolation(app, db):
    a = _make_school(db, slug="orga")
    b = _make_school(db, slug="orgb")
    _admin(app, a).post("/api/assignments", json={"title": "secret", "batch_id": a["batch"].id})
    assert _admin(app, b).get("/api/assignments").get_json() == []
