"""Fees / payments tests (HTTP layer, real auth + tenant scoping)."""

from datetime import date

from werkzeug.security import generate_password_hash


def _make_school(db, *, slug, n_students=3, org_pw="OrgPass123", admin_pw="AdminPass1"):
    from models import Organization, User, Batch, Student

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
    students = []
    for i in range(n_students):
        s = Student(organization_id=org.id, student_id=f"{slug.upper()}STU{i+1}",
                    admission_no=f"{slug.upper()}ADM{i+1}", first_name=f"S{i+1}",
                    last_name="T", class_grade="9", section="A", roll_no=i + 1,
                    admission_date=date(2024, 4, 1), status="Active")
        db.session.add(s)
        students.append(s)
    db.session.commit()
    return {"org": org, "admin": admin, "batch": batch, "students": students,
            "org_pw": org_pw, "admin_pw": admin_pw}


def _client(app, slug, email, org_pw, user_pw):
    c = app.test_client()
    assert c.post("/api/organizations/login",
                  json={"identifier": slug, "password": org_pw}).status_code == 200
    assert c.post("/api/auth/login", json={"email": email, "password": user_pw}).status_code == 200
    return c


def _admin(app, s):
    return _client(app, s["org"].slug, s["admin"].email, s["org_pw"], s["admin_pw"])


def test_structure_generate_creates_invoices_idempotently(app, db):
    s = _make_school(db, slug="alpha", n_students=3)
    admin = _admin(app, s)
    struct = admin.post("/api/fees/structures", json={
        "name": "Term 1", "amount": 1000, "grade": "9"}).get_json()

    r = admin.post(f"/api/fees/structures/{struct['id']}/generate")
    assert r.status_code == 200 and r.get_json()["created"] == 3
    # Running again creates nothing new.
    r2 = admin.post(f"/api/fees/structures/{struct['id']}/generate")
    assert r2.get_json()["created"] == 0

    invoices = admin.get("/api/fees/invoices").get_json()
    assert len(invoices) == 3
    assert all(i["status"] == "pending" and i["amount"] == 1000 for i in invoices)


def test_payment_transitions_status_and_blocks_overpay(app, db):
    s = _make_school(db, slug="beta", n_students=1)
    admin = _admin(app, s)
    struct = admin.post("/api/fees/structures", json={"name": "Bus", "amount": 500}).get_json()
    admin.post(f"/api/fees/structures/{struct['id']}/generate")
    inv = admin.get("/api/fees/invoices").get_json()[0]

    # Partial payment.
    r = admin.post(f"/api/fees/invoices/{inv['id']}/payments", json={"amount": 200})
    assert r.status_code == 201
    assert r.get_json()["invoice"]["status"] == "partial"

    # Overpayment rejected.
    bad = admin.post(f"/api/fees/invoices/{inv['id']}/payments", json={"amount": 999})
    assert bad.status_code == 400

    # Pay the rest -> paid.
    r2 = admin.post(f"/api/fees/invoices/{inv['id']}/payments", json={"amount": 300})
    assert r2.get_json()["invoice"]["status"] == "paid"
    assert r2.get_json()["invoice"]["balance"] == 0


def test_summary_totals(app, db):
    s = _make_school(db, slug="gamma", n_students=2)
    admin = _admin(app, s)
    struct = admin.post("/api/fees/structures", json={"name": "Fee", "amount": 1000}).get_json()
    admin.post(f"/api/fees/structures/{struct['id']}/generate")
    inv = admin.get("/api/fees/invoices").get_json()[0]
    admin.post(f"/api/fees/invoices/{inv['id']}/payments", json={"amount": 1000})

    summary = admin.get("/api/fees/summary").get_json()
    assert summary["billed"] == 2000
    assert summary["collected"] == 1000
    assert summary["outstanding"] == 1000


def test_parent_can_view_only_their_childs_invoices(app, db):
    s = _make_school(db, slug="delta", n_students=2)
    admin = _admin(app, s)
    struct = admin.post("/api/fees/structures", json={"name": "Fee", "amount": 800}).get_json()
    admin.post(f"/api/fees/structures/{struct['id']}/generate")

    child = s["students"][0]
    created = admin.post("/api/admin/parents", json={
        "name": "P", "email": "p@delta.test", "student_ids": [child.id]}).get_json()
    parent = _client(app, "delta", "p@delta.test", s["org_pw"],
                     created["credentials"]["temporary_password"])

    own = parent.get(f"/api/fees/student/{child.id}")
    assert own.status_code == 200
    assert own.get_json()["totals"]["billed"] == 800

    other = s["students"][1]
    assert parent.get(f"/api/fees/student/{other.id}").status_code == 403


def test_fees_tenant_isolation(app, db):
    a = _make_school(db, slug="orga", n_students=1)
    b = _make_school(db, slug="orgb", n_students=1)
    ca = _admin(app, a)
    struct = ca.post("/api/fees/structures", json={"name": "Fee", "amount": 100}).get_json()
    ca.post(f"/api/fees/structures/{struct['id']}/generate")

    cb = _admin(app, b)
    assert cb.get("/api/fees/invoices").get_json() == []
    assert cb.post(f"/api/fees/structures/{struct['id']}/generate").status_code == 404


def test_students_cannot_create_structures(app, db):
    s = _make_school(db, slug="eps", n_students=1)
    from models import User
    su = User(name="Stu", email="stu@eps.test", role="student",
              organization_id=s["org"].id, password_hash=generate_password_hash("StudPass1"))
    db.session.add(su)
    db.session.flush()
    s["students"][0].user_id = su.id
    db.session.commit()
    stu = _client(app, "eps", "stu@eps.test", s["org_pw"], "StudPass1")
    assert stu.post("/api/fees/structures", json={"name": "x", "amount": 1}).status_code == 403
