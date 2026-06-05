"""Parent role + announcements tests (HTTP layer, real auth + tenant scoping)."""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_school(db, *, slug, org_pw="OrgPass123", admin_pw="AdminPass1"):
    """Org with admin, a class (9-A), a student (with login) and a teacher."""
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
    student = Student(
        organization_id=org.id, student_id=f"{slug.upper()}STU1",
        admission_no=f"{slug.upper()}ADM1", first_name="Kid", last_name="One",
        class_grade="9", section="A", roll_no=1, admission_date=date(2024, 4, 1),
        status="Active", user_id=stu_user.id,
    )
    db.session.add(student)

    # A teacher assigned to a *different* class (9-B) for negative tests.
    other = Batch(organization_id=org.id, grade="9", section="B", subject_ids=[])
    db.session.add(other)
    db.session.flush()
    t_user = User(name="Teach", email=f"teach@{slug}.test", role="teacher",
                  organization_id=org.id, password_hash=generate_password_hash("TeachPass1"))
    db.session.add(t_user)
    db.session.flush()
    db.session.add(Teacher(organization_id=org.id, user_id=t_user.id, name="Teach",
                           email=f"teach@{slug}.test", assigned_batch_ids=[other.id]))
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


def _admin_client(app, s):
    return _client(app, s["org"].slug, s["admin"].email, s["org_pw"], s["admin_pw"])


def _create_parent(admin_client, s, email="parent@alpha.test", student_ids=None):
    r = admin_client.post("/api/admin/parents", json={
        "name": "Parent One", "email": email,
        "student_ids": student_ids if student_ids is not None else [s["student"].id],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


# ---------------------------------------------------------------------------
# Parent provisioning + linkage
# ---------------------------------------------------------------------------

def test_admin_creates_parent_and_parent_sees_children(app, db):
    s = _make_school(db, slug="alpha")
    admin = _admin_client(app, s)
    created = _create_parent(admin, s)
    assert created["credentials"]["temporary_password"]
    assert len(created["children"]) == 1

    parent = _client(app, "alpha", "parent@alpha.test", s["org_pw"],
                     created["credentials"]["temporary_password"])
    kids = parent.get("/api/parent/children").get_json()
    assert len(kids) == 1
    assert kids[0]["student_id"] == s["student"].id


def test_parent_needs_at_least_one_child(app, db):
    s = _make_school(db, slug="beta")
    admin = _admin_client(app, s)
    r = admin.post("/api/admin/parents", json={
        "name": "P", "email": "p@beta.test", "student_ids": []})
    assert r.status_code == 400


def test_parent_can_view_only_their_childs_records(app, db):
    s = _make_school(db, slug="gamma")
    admin = _admin_client(app, s)

    # Mark some attendance + publish an exam result for the child.
    sid = s["student"].id
    admin.post("/api/attendance/mark", json={
        "batch_id": s["batch"].id, "date": date.today().isoformat(), "period_number": 0,
        "records": [{"student_id": sid, "status": "present"}]})
    exam = admin.post("/api/exams", json={"name": "T1", "max_marks": 100}).get_json()
    admin.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": s["batch"].id, "subject_id": s["subject"].id, "max_marks": 100,
        "records": [{"student_id": sid, "marks_obtained": 80}]})
    admin.post(f"/api/exams/{exam['id']}/publish", json={"published": True})

    created = _create_parent(admin, s)
    parent = _client(app, "gamma", "parent@alpha.test", s["org_pw"],
                     created["credentials"]["temporary_password"])

    att = parent.get(f"/api/attendance/student/{sid}")
    assert att.status_code == 200
    assert att.get_json()["summary"]["present"] == 1

    res = parent.get(f"/api/exams/student/{sid}").get_json()
    assert len(res["results"]) == 1
    assert res["results"][0]["percentage"] == 80.0

    # An unlinked student is forbidden.
    from models import User, Student
    other_user = User(name="K2", email="k2@gamma.test", role="student",
                      organization_id=s["org"].id, password_hash=generate_password_hash("x"))
    db.session.add(other_user)
    db.session.flush()
    other = Student(organization_id=s["org"].id, student_id="GAMMASTU2",
                    admission_no="GAMMAADM2", first_name="K", last_name="Two",
                    class_grade="9", section="A", roll_no=2,
                    admission_date=date(2024, 4, 1), status="Active", user_id=other_user.id)
    db.session.add(other)
    db.session.commit()
    assert parent.get(f"/api/attendance/student/{other.id}").status_code == 403
    assert parent.get(f"/api/exams/student/{other.id}").status_code == 403


def test_parent_only_sees_published_results(app, db):
    s = _make_school(db, slug="delta")
    admin = _admin_client(app, s)
    sid = s["student"].id
    exam = admin.post("/api/exams", json={"name": "Draft", "max_marks": 100}).get_json()
    admin.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": s["batch"].id, "subject_id": s["subject"].id, "max_marks": 100,
        "records": [{"student_id": sid, "marks_obtained": 90}]})
    # NOT published.
    created = _create_parent(admin, s)
    parent = _client(app, "delta", "parent@alpha.test", s["org_pw"],
                     created["credentials"]["temporary_password"])
    assert parent.get(f"/api/exams/student/{sid}").get_json()["results"] == []


# ---------------------------------------------------------------------------
# Announcements: audience visibility
# ---------------------------------------------------------------------------

def _post(admin_client, **kw):
    r = admin_client.post("/api/announcements", json=kw)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def test_announcement_audience_visibility(app, db):
    s = _make_school(db, slug="epsilon")
    admin = _admin_client(app, s)
    created = _create_parent(admin, s)
    parent = _client(app, "epsilon", "parent@alpha.test", s["org_pw"],
                     created["credentials"]["temporary_password"])
    student = _client(app, "epsilon", s["student_user"].email, s["org_pw"], "KidPass123")
    teacher = _client(app, "epsilon", s["teacher_user"].email, s["org_pw"], "TeachPass1")

    _post(admin, title="Everyone", body="hi all", audience="all")
    _post(admin, title="Parents only", body="pta", audience="parents")
    _post(admin, title="Teachers only", body="staff", audience="teachers")

    def titles(client):
        return {a["title"] for a in client.get("/api/announcements").get_json()}

    assert titles(parent) == {"Everyone", "Parents only"}
    assert titles(student) == {"Everyone"}
    assert titles(teacher) == {"Everyone", "Teachers only"}
    # Admin sees all three.
    assert titles(admin) == {"Everyone", "Parents only", "Teachers only"}


def test_class_scoped_announcement_only_for_that_class(app, db):
    s = _make_school(db, slug="zeta")
    admin = _admin_client(app, s)
    created = _create_parent(admin, s)
    parent = _client(app, "zeta", "parent@alpha.test", s["org_pw"],
                     created["credentials"]["temporary_password"])

    # Targeted at the child's class (9-A) -> visible to that parent.
    _post(admin, title="9A note", body="for 9A", audience="parents", batch_id=s["batch"].id)
    # Targeted at a different class (9-B) -> hidden from this parent.
    _post(admin, title="9B note", body="for 9B", audience="parents", batch_id=s["other_batch"].id)

    titles = {a["title"] for a in parent.get("/api/announcements").get_json()}
    assert titles == {"9A note"}


def test_teacher_can_only_post_to_their_classes(app, db):
    s = _make_school(db, slug="eta")
    teacher = _client(app, "eta", s["teacher_user"].email, s["org_pw"], "TeachPass1")

    # Teacher is assigned to other_batch (9-B); posting there is allowed.
    ok = teacher.post("/api/announcements", json={
        "title": "ok", "body": "x", "audience": "students", "batch_id": s["other_batch"].id})
    assert ok.status_code == 201

    # Posting to a class they don't teach (9-A) is forbidden.
    bad = teacher.post("/api/announcements", json={
        "title": "no", "body": "x", "audience": "students", "batch_id": s["batch"].id})
    assert bad.status_code == 403

    # Posting org-wide (no batch) is forbidden for teachers.
    org_wide = teacher.post("/api/announcements", json={
        "title": "no2", "body": "x", "audience": "all"})
    assert org_wide.status_code == 403


def test_announcement_tenant_isolation(app, db):
    a = _make_school(db, slug="orga")
    b = _make_school(db, slug="orgb")
    _post(_admin_client(app, a), title="A-secret", body="x", audience="all")
    titles = {x["title"] for x in _admin_client(app, b).get("/api/announcements").get_json()}
    assert "A-secret" not in titles
