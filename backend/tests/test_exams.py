"""Exams / gradebook / report-card tests (HTTP layer, real auth + scoping)."""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_school(db, *, slug, n_students=3, org_pw="OrgPass123", admin_pw="AdminPass1"):
    from models import Organization, User, Batch, Student, Subject

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

    students = []
    for i in range(n_students):
        s = Student(
            organization_id=org.id, student_id=f"{slug.upper()}STU{i+1}",
            admission_no=f"{slug.upper()}ADM{i+1}", first_name=f"S{i+1}",
            last_name="T", class_grade="9", section="A", roll_no=i + 1,
            admission_date=date(2024, 4, 1), status="Active",
        )
        db.session.add(s)
        students.append(s)
    db.session.commit()
    return {"org": org, "admin": admin, "subject": subject, "batch": batch,
            "students": students, "org_pw": org_pw, "admin_pw": admin_pw}


def _client_as(app, slug, email, org_pw, user_pw):
    client = app.test_client()
    assert client.post("/api/organizations/login",
                       json={"identifier": slug, "password": org_pw}).status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": email, "password": user_pw}).status_code == 200
    return client


def _admin_client(app, school):
    return _client_as(app, school["org"].slug, school["admin"].email,
                      school["org_pw"], school["admin_pw"])


def _create_exam(client, **kw):
    payload = {"name": "Mid Term", "max_marks": 100}
    payload.update(kw)
    r = client.post("/api/exams", json=payload)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def test_create_list_and_student_visibility(app, db):
    school = _make_school(db, slug="alpha", n_students=1)
    client = _admin_client(app, school)
    exam = _create_exam(client)

    # Admin sees the draft.
    exams = client.get("/api/exams").get_json()
    assert any(e["id"] == exam["id"] for e in exams)

    # Student does NOT see a draft exam.
    from models import User, Student
    suser = User(name="Stu", email="stu@alpha.test", role="student",
                 organization_id=school["org"].id,
                 password_hash=generate_password_hash("StudPass1"))
    db.session.add(suser)
    db.session.flush()
    school["students"][0].user_id = suser.id
    db.session.commit()

    sclient = _client_as(app, "alpha", "stu@alpha.test", school["org_pw"], "StudPass1")
    assert sclient.get("/api/exams").get_json() == []


def test_marks_entry_grade_and_results(app, db):
    school = _make_school(db, slug="beta", n_students=2)
    client = _admin_client(app, school)
    exam = _create_exam(client, max_marks=100)
    batch_id = school["batch"].id
    subj_id = school["subject"].id
    s0, s1 = [s.id for s in school["students"]]

    r = client.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": batch_id, "subject_id": subj_id, "max_marks": 100,
        "records": [
            {"student_id": s0, "marks_obtained": 95},
            {"student_id": s1, "marks_obtained": 45},
        ],
    })
    assert r.status_code == 200 and r.get_json()["saved"] == 2

    # Marksheet reflects grades (A1 for 95, C2 for 45).
    sheet = client.get(f"/api/exams/{exam['id']}/marksheet",
                       query_string={"batch_id": batch_id, "subject_id": subj_id}).get_json()
    grades = {row["student_id"]: row["grade"] for row in sheet["students"]}
    assert grades[s0] == "A1"
    assert grades[s1] == "C2"

    # Results: ranks + overall percentage.
    results = client.get(f"/api/exams/{exam['id']}/results",
                         query_string={"batch_id": batch_id}).get_json()
    by_id = {r["student_id"]: r for r in results["students"]}
    assert by_id[s0]["percentage"] == 95.0
    assert by_id[s0]["overall_grade"] == "A1"
    assert by_id[s0]["rank"] == 1
    assert by_id[s1]["rank"] == 2


def test_marks_upsert_in_place(app, db):
    school = _make_school(db, slug="gamma", n_students=1)
    client = _admin_client(app, school)
    exam = _create_exam(client)
    sid = school["students"][0].id
    body = {"batch_id": school["batch"].id, "subject_id": school["subject"].id, "max_marks": 100}

    client.post(f"/api/exams/{exam['id']}/marks", json={**body,
                "records": [{"student_id": sid, "marks_obtained": 50}]})
    client.post(f"/api/exams/{exam['id']}/marks", json={**body,
                "records": [{"student_id": sid, "marks_obtained": 88}]})

    from models import Mark
    rows = Mark.query.filter_by(student_id=sid, exam_id=exam["id"]).all()
    assert len(rows) == 1
    assert rows[0].marks_obtained == 88
    assert rows[0].grade == "A2"


def test_marks_out_of_range_rejected(app, db):
    school = _make_school(db, slug="delta", n_students=1)
    client = _admin_client(app, school)
    exam = _create_exam(client, max_marks=50)
    r = client.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": school["batch"].id, "subject_id": school["subject"].id, "max_marks": 50,
        "records": [{"student_id": school["students"][0].id, "marks_obtained": 80}],
    })
    assert r.status_code == 400


def test_absent_has_no_grade(app, db):
    school = _make_school(db, slug="eps", n_students=1)
    client = _admin_client(app, school)
    exam = _create_exam(client)
    sid = school["students"][0].id
    client.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": school["batch"].id, "subject_id": school["subject"].id, "max_marks": 100,
        "records": [{"student_id": sid, "is_absent": True}],
    })
    from models import Mark
    m = Mark.query.filter_by(student_id=sid, exam_id=exam["id"]).first()
    assert m.is_absent is True
    assert m.grade is None


def test_exam_marks_tenant_isolation(app, db):
    a = _make_school(db, slug="orga", n_students=1)
    b = _make_school(db, slug="orgb", n_students=1)
    ca = _admin_client(app, a)
    exam_a = _create_exam(ca)

    # Org B cannot see or write to org A's exam.
    cb = _admin_client(app, b)
    assert cb.get(f"/api/exams/{exam_a['id']}/results",
                  query_string={"batch_id": a["batch"].id}).status_code == 404
    r = cb.post(f"/api/exams/{exam_a['id']}/marks", json={
        "batch_id": a["batch"].id, "subject_id": a["subject"].id,
        "records": [{"student_id": a["students"][0].id, "marks_obtained": 10}],
    })
    assert r.status_code == 404


def test_student_sees_results_only_after_publish(app, db):
    school = _make_school(db, slug="zeta", n_students=1)
    client = _admin_client(app, school)
    exam = _create_exam(client)
    sid = school["students"][0].id
    client.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": school["batch"].id, "subject_id": school["subject"].id, "max_marks": 100,
        "records": [{"student_id": sid, "marks_obtained": 70}],
    })

    from models import User
    suser = User(name="Stu", email="stu@zeta.test", role="student",
                 organization_id=school["org"].id,
                 password_hash=generate_password_hash("StudPass1"))
    db.session.add(suser)
    db.session.flush()
    school["students"][0].user_id = suser.id
    db.session.commit()
    sclient = _client_as(app, "zeta", "stu@zeta.test", school["org_pw"], "StudPass1")

    # Before publish: no results visible.
    res = sclient.get(f"/api/exams/student/{sid}").get_json()
    assert res["results"] == []

    # After publish: the result appears.
    assert client.post(f"/api/exams/{exam['id']}/publish", json={"published": True}).status_code == 200
    res = sclient.get(f"/api/exams/student/{sid}").get_json()
    assert len(res["results"]) == 1
    assert res["results"][0]["percentage"] == 70.0


def test_teacher_limited_to_their_classes(app, db):
    from models import User, Teacher, Batch

    school = _make_school(db, slug="eta", n_students=1)
    org = school["org"]
    other = school["batch"]  # 9-A, teacher NOT assigned

    taught = Batch(organization_id=org.id, grade="9", section="B", subject_ids=[])
    db.session.add(taught)
    db.session.flush()
    tuser = User(name="T", email="t@eta.test", role="teacher", organization_id=org.id,
                 password_hash=generate_password_hash("TeachPass1"))
    db.session.add(tuser)
    db.session.flush()
    db.session.add(Teacher(organization_id=org.id, user_id=tuser.id, name="T",
                           email="t@eta.test", assigned_batch_ids=[taught.id]))
    db.session.commit()

    client = _admin_client(app, school)
    exam = _create_exam(client)

    tclient = _client_as(app, "eta", "t@eta.test", school["org_pw"], "TeachPass1")
    r = tclient.post(f"/api/exams/{exam['id']}/marks", json={
        "batch_id": other.id, "subject_id": school["subject"].id,
        "records": [{"student_id": school["students"][0].id, "marks_obtained": 50}],
    })
    assert r.status_code == 403
