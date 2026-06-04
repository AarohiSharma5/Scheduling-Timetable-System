"""Attendance module tests (HTTP layer, with real auth + tenant scoping)."""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_school(db, *, slug, n_students=3, org_pw="OrgPass123", admin_pw="AdminPass1"):
    """Create an org with an admin, one class (Grade 9-A) and some students."""
    from models import Organization, User, Batch, Student

    org = Organization(name=slug.title(), slug=slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()

    admin = User(name="Admin", email=f"admin@{slug}.test", role="admin",
                 organization_id=org.id, password_hash=generate_password_hash(admin_pw))
    db.session.add(admin)

    batch = Batch(organization_id=org.id, grade="9", section="A",
                  student_count=n_students, subject_ids=[])
    db.session.add(batch)
    db.session.flush()

    students = []
    for i in range(n_students):
        s = Student(
            organization_id=org.id, student_id=f"{slug.upper()}STU{i+1}",
            admission_no=f"{slug.upper()}ADM{i+1}", first_name=f"S{i+1}",
            last_name="Test", class_grade="9", section="A", roll_no=i + 1,
            admission_date=date(2024, 4, 1), status="Active",
        )
        db.session.add(s)
        students.append(s)
    db.session.commit()
    return {"org": org, "admin": admin, "batch": batch, "students": students,
            "org_pw": org_pw, "admin_pw": admin_pw}


def _client_as(app, slug, email, org_pw, user_pw):
    client = app.test_client()
    r = client.post("/api/organizations/login",
                    json={"identifier": slug, "password": org_pw})
    assert r.status_code == 200, r.get_json()
    r = client.post("/api/auth/login", json={"email": email, "password": user_pw})
    assert r.status_code == 200, r.get_json()
    return client


def _admin_client(app, school):
    return _client_as(app, school["org"].slug, school["admin"].email,
                      school["org_pw"], school["admin_pw"])


def test_mark_and_summary_roundtrip(app, db):
    school = _make_school(db, slug="alpha", n_students=3)
    client = _admin_client(app, school)
    batch_id = school["batch"].id
    sids = [s.id for s in school["students"]]
    today = date.today().isoformat()

    r = client.post("/api/attendance/mark", json={
        "batch_id": batch_id, "date": today, "period_number": 0,
        "records": [
            {"student_id": sids[0], "status": "present"},
            {"student_id": sids[1], "status": "absent"},
            {"student_id": sids[2], "status": "late"},
        ],
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body["saved"] == 3
    assert body["summary"] == {"present": 1, "absent": 1, "late": 1, "excused": 0}

    # Summary: late counts as attended -> 2/3 present-ish.
    r = client.get(f"/api/attendance/summary?batch_id={batch_id}")
    rows = {row["student_id"]: row for row in r.get_json()["students"]}
    assert rows[sids[1]]["absent"] == 1
    assert rows[sids[1]]["percentage"] == 0.0
    assert rows[sids[2]]["late"] == 1
    assert rows[sids[2]]["percentage"] == 100.0


def test_remarking_updates_in_place(app, db):
    school = _make_school(db, slug="beta", n_students=1)
    client = _admin_client(app, school)
    batch_id = school["batch"].id
    sid = school["students"][0].id
    today = date.today().isoformat()

    client.post("/api/attendance/mark", json={
        "batch_id": batch_id, "date": today,
        "records": [{"student_id": sid, "status": "absent"}],
    })
    client.post("/api/attendance/mark", json={
        "batch_id": batch_id, "date": today,
        "records": [{"student_id": sid, "status": "present"}],
    })

    from models import AttendanceRecord
    recs = AttendanceRecord.query.filter_by(student_id=sid, period_number=0).all()
    assert len(recs) == 1            # upsert, not duplicate
    assert recs[0].status == "present"


def test_future_date_rejected(app, db):
    school = _make_school(db, slug="gamma", n_students=1)
    client = _admin_client(app, school)
    r = client.post("/api/attendance/mark", json={
        "batch_id": school["batch"].id, "date": "2999-01-01",
        "records": [{"student_id": school["students"][0].id, "status": "present"}],
    })
    assert r.status_code == 400


def test_attendance_is_tenant_scoped(app, db):
    """A user in org B can never mark org A's class, and totals don't leak."""
    a = _make_school(db, slug="orga", n_students=2)
    b = _make_school(db, slug="orgb", n_students=2)

    client_a = _admin_client(app, a)
    today = date.today().isoformat()
    client_a.post("/api/attendance/mark", json={
        "batch_id": a["batch"].id, "date": today,
        "records": [{"student_id": s.id, "status": "present"} for s in a["students"]],
    })

    # Org B admin cannot mark org A's class (404 - not in their org).
    client_b = _admin_client(app, b)
    r = client_b.post("/api/attendance/mark", json={
        "batch_id": a["batch"].id, "date": today,
        "records": [{"student_id": a["students"][0].id, "status": "absent"}],
    })
    assert r.status_code == 404

    # Org B's "today" snapshot must not count org A's marks.
    snap = client_b.get("/api/attendance/today").get_json()
    assert snap["total_marked"] == 0


def test_teacher_limited_to_their_classes(app, db):
    """A teacher may only mark a class they're assigned to / class-teacher of."""
    from models import User, Teacher, Batch

    school = _make_school(db, slug="delta", n_students=2)
    org = school["org"]

    # A second class the teacher is NOT assigned to is school["batch"] (9-A).
    other_batch = school["batch"]

    # Class the teacher IS assigned to (9-B, no students needed for this check).
    taught = Batch(organization_id=org.id, grade="9", section="B", subject_ids=[])
    db.session.add(taught)
    db.session.flush()

    tuser = User(name="T", email="t@delta.test", role="teacher",
                 organization_id=org.id, password_hash=generate_password_hash("TeachPass1"))
    db.session.add(tuser)
    db.session.flush()
    teacher = Teacher(organization_id=org.id, user_id=tuser.id, name="T",
                      email="t@delta.test", assigned_batch_ids=[taught.id])
    db.session.add(teacher)
    db.session.commit()

    client = _client_as(app, "delta", "t@delta.test", school["org_pw"], "TeachPass1")
    today = date.today().isoformat()

    # Allowed class shows up in /classes; the other one does not.
    labels = {c["batch_id"] for c in client.get("/api/attendance/classes").get_json()}
    assert taught.id in labels
    assert other_batch.id not in labels

    # Marking the un-assigned class is forbidden.
    r = client.post("/api/attendance/mark", json={
        "batch_id": other_batch.id, "date": today,
        "records": [{"student_id": school["students"][0].id, "status": "absent"}],
    })
    assert r.status_code == 403


def test_student_sees_only_own_attendance(app, db):
    from models import User, Student

    school = _make_school(db, slug="epsilon", n_students=2)
    org = school["org"]
    s0, s1 = school["students"]

    # Give student s0 a login.
    suser = User(name="Stu", email="stu@epsilon.test", role="student",
                 organization_id=org.id, password_hash=generate_password_hash("StudPass1"))
    db.session.add(suser)
    db.session.flush()
    s0.user_id = suser.id
    db.session.commit()

    client = _client_as(app, "epsilon", "stu@epsilon.test", school["org_pw"], "StudPass1")

    assert client.get(f"/api/attendance/student/{s0.id}").status_code == 200
    assert client.get(f"/api/attendance/student/{s1.id}").status_code == 403
