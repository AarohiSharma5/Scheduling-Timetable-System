"""Tests for calendar, library, transport, inventory, analytics, messaging."""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_school(db, *, slug, org_pw="OrgPass123", admin_pw="AdminPass1"):
    from models import Organization, User, Batch, Student, Teacher

    org = Organization(name=slug.title(), slug=slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()
    admin = User(name="Admin", email=f"admin@{slug}.test", role="admin",
                 organization_id=org.id, password_hash=generate_password_hash(admin_pw))
    db.session.add(admin)
    batch = Batch(organization_id=org.id, grade="9", section="A", subject_ids=[])
    db.session.add(batch)
    db.session.flush()

    stu_user = User(name="Kid", email=f"kid@{slug}.test", role="student",
                    organization_id=org.id, password_hash=generate_password_hash("KidPass123"))
    db.session.add(stu_user)
    db.session.flush()
    students = []
    for i in range(2):
        s = Student(organization_id=org.id, student_id=f"{slug.upper()}STU{i+1}",
                    admission_no=f"{slug.upper()}ADM{i+1}", first_name=f"S{i+1}", last_name="T",
                    class_grade="9", section="A", roll_no=i + 1, admission_date=date(2024, 4, 1),
                    status="Active", user_id=stu_user.id if i == 0 else None)
        db.session.add(s)
        students.append(s)

    t_user = User(name="Teach", email=f"teach@{slug}.test", role="teacher",
                  organization_id=org.id, password_hash=generate_password_hash("TeachPass1"))
    db.session.add(t_user)
    db.session.flush()
    db.session.add(Teacher(organization_id=org.id, user_id=t_user.id, name="Teach",
                           email=f"teach@{slug}.test", assigned_batch_ids=[batch.id]))
    db.session.commit()
    return {"org": org, "admin": admin, "batch": batch, "students": students,
            "student_user": stu_user, "teacher_user": t_user,
            "org_pw": org_pw, "admin_pw": admin_pw}


def _client(app, slug, email, org_pw, user_pw):
    c = app.test_client()
    assert c.post("/api/organizations/login",
                  json={"identifier": slug, "password": org_pw}).status_code == 200
    assert c.post("/api/auth/login", json={"email": email, "password": user_pw}).status_code == 200
    return c


def _admin(app, s):
    return _client(app, s["org"].slug, s["admin"].email, s["org_pw"], s["admin_pw"])


def _student(app, s):
    return _client(app, s["org"].slug, s["student_user"].email, s["org_pw"], "KidPass123")


def _teacher(app, s):
    return _client(app, s["org"].slug, s["teacher_user"].email, s["org_pw"], "TeachPass1")


# --------------------------------------------------------------------------- calendar

def test_calendar_create_and_visibility(app, db):
    s = _make_school(db, slug="cal")
    admin = _admin(app, s)
    r = admin.post("/api/calendar", json={"title": "Diwali", "event_type": "holiday",
                                          "start_date": "2026-11-08"})
    assert r.status_code == 201
    # Student can view but not create.
    student = _student(app, s)
    assert len(student.get("/api/calendar").get_json()) == 1
    assert student.post("/api/calendar", json={"title": "x", "start_date": "2026-01-01"}).status_code == 403


def test_calendar_tenant_isolation(app, db):
    a = _make_school(db, slug="cala")
    b = _make_school(db, slug="calb")
    _admin(app, a).post("/api/calendar", json={"title": "A-only", "start_date": "2026-05-01"})
    assert _admin(app, b).get("/api/calendar").get_json() == []


# --------------------------------------------------------------------------- library

def test_library_issue_and_return_adjust_copies(app, db):
    s = _make_school(db, slug="lib")
    admin = _admin(app, s)
    book = admin.post("/api/library/books", json={"title": "Algebra", "total_copies": 1}).get_json()
    assert book["available_copies"] == 1

    loan = admin.post("/api/library/loans", json={
        "book_id": book["id"], "student_id": s["students"][0].id}).get_json()
    assert admin.get("/api/library/books").get_json()[0]["available_copies"] == 0
    # No copies left -> second issue blocked.
    assert admin.post("/api/library/loans", json={
        "book_id": book["id"], "student_id": s["students"][1].id}).status_code == 400

    ret = admin.post(f"/api/library/loans/{loan['id']}/return")
    assert ret.status_code == 200 and ret.get_json()["status"] == "returned"
    assert admin.get("/api/library/books").get_json()[0]["available_copies"] == 1


def test_library_student_sees_own_loans(app, db):
    s = _make_school(db, slug="lib2")
    admin = _admin(app, s)
    book = admin.post("/api/library/books", json={"title": "Physics"}).get_json()
    admin.post("/api/library/loans", json={"book_id": book["id"], "student_id": s["students"][0].id})
    student = _student(app, s)
    res = student.get(f"/api/library/student/{s['students'][0].id}")
    assert res.status_code == 200 and len(res.get_json()["loans"]) == 1
    # Cannot read another student's loans.
    assert student.get(f"/api/library/student/{s['students'][1].id}").status_code == 403


# --------------------------------------------------------------------------- transport

def test_transport_assign_capacity_and_view(app, db):
    s = _make_school(db, slug="trn")
    admin = _admin(app, s)
    route = admin.post("/api/transport/routes", json={"name": "R1", "capacity": 1}).get_json()
    assert admin.post(f"/api/transport/routes/{route['id']}/students",
                      json={"student_id": s["students"][0].id, "stop_name": "Gate"}).status_code == 201
    # Capacity 1 reached.
    assert admin.post(f"/api/transport/routes/{route['id']}/students",
                      json={"student_id": s["students"][1].id}).status_code == 400

    student = _student(app, s)
    res = student.get(f"/api/transport/student/{s['students'][0].id}")
    assert res.status_code == 200 and res.get_json()["transport"][0]["route_name"] == "R1"


# --------------------------------------------------------------------------- inventory

def test_inventory_adjust_guards_negative(app, db):
    s = _make_school(db, slug="inv")
    admin = _admin(app, s)
    item = admin.post("/api/inventory", json={"name": "Chalk", "quantity": 5, "min_quantity": 2}).get_json()
    assert admin.post(f"/api/inventory/{item['id']}/adjust", json={"delta": -10}).status_code == 400
    ok = admin.post(f"/api/inventory/{item['id']}/adjust", json={"delta": -4})
    assert ok.status_code == 200 and ok.get_json()["quantity"] == 1
    assert ok.get_json()["low_stock"] is True
    summary = admin.get("/api/inventory/summary").get_json()
    assert summary["low_stock_count"] == 1


def test_inventory_requires_staff(app, db):
    s = _make_school(db, slug="inv2")
    assert _student(app, s).get("/api/inventory").status_code == 403


# --------------------------------------------------------------------------- analytics

def test_analytics_overview_keys(app, db):
    s = _make_school(db, slug="an")
    admin = _admin(app, s)
    data = admin.get("/api/analytics/overview").get_json()
    for key in ("students", "attendance", "fees", "exams", "library", "transport", "inventory"):
        assert key in data
    assert data["students"]["total"] == 2
    # Non-staff blocked.
    assert _student(app, s).get("/api/analytics/overview").status_code == 403


# --------------------------------------------------------------------------- messaging

def test_messaging_parent_staff_and_read(app, db):
    s = _make_school(db, slug="msg")
    teacher_uid = s["teacher_user"].id
    student = _student(app, s)
    # Student can message a teacher (staff).
    sent = student.post("/api/messages", json={"recipient_id": teacher_uid, "body": "Hi sir"})
    assert sent.status_code == 201

    teacher = _teacher(app, s)
    convs = teacher.get("/api/messages/conversations").get_json()
    assert convs[0]["unread"] == 1
    assert teacher.get("/api/messages/unread-count").get_json()["unread"] == 1
    # Opening the thread marks it read.
    teacher.get(f"/api/messages/thread/{s['student_user'].id}")
    assert teacher.get("/api/messages/unread-count").get_json()["unread"] == 0


def test_messaging_student_cannot_message_student(app, db):
    s = _make_school(db, slug="msg2")
    from models import User
    other = User(name="Stu2", email="stu2@msg2.test", role="student",
                 organization_id=s["org"].id, password_hash=generate_password_hash("x"))
    db.session.add(other)
    db.session.commit()
    student = _student(app, s)
    assert student.post("/api/messages", json={"recipient_id": other.id, "body": "yo"}).status_code == 403


def test_messaging_tenant_isolation(app, db):
    a = _make_school(db, slug="msga")
    b = _make_school(db, slug="msgb")
    # Cannot message a user from another org.
    assert _admin(app, a).post("/api/messages", json={
        "recipient_id": b["teacher_user"].id, "body": "x"}).status_code == 403
