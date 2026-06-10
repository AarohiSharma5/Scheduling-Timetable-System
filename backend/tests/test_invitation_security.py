"""Invitation security: hashed tokens, single-use, Google acceptance rules,
token versioning (logout-all-devices)."""

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


def _invite(app, s, email="newuser@x.test", role="teacher"):
    admin = _admin_client(app, s)
    r = admin.post("/api/invitations", json={"email": email, "name": "New", "role": role})
    assert r.status_code == 201, r.get_json()
    link = r.get_json()["invite_link"]
    return link.rsplit("/", 1)[-1]  # the raw token


def test_tokens_are_stored_hashed(app, db):
    from models import Invitation
    s = _school(db, slug="hashinv")
    raw = _invite(app, s)
    inv = Invitation.query.filter_by(organization_id=s["org"].id).first()
    # The raw token must never appear in the database.
    assert raw not in (inv.token_hash or "")
    assert len(inv.token_hash) == 64  # sha256 hex


def test_invitation_is_single_use(app, db):
    s = _school(db, slug="singleuse")
    raw = _invite(app, s)
    c = app.test_client()
    body = {"name": "New User", "password": "GoodPass1"}
    assert c.post(f"/api/invitations/accept/{raw}", json=body).status_code == 201
    # Second use must fail.
    assert c.post(f"/api/invitations/accept/{raw}", json=body).status_code in (404, 409)


def test_bogus_token_rejected(app, db):
    _school(db, slug="bogustok")
    c = app.test_client()
    assert c.get("/api/invitations/accept/not-a-real-token").status_code == 404


def test_google_accept_email_mismatch_denied(app, db, monkeypatch):
    import routes
    from models import User
    s = _school(db, slug="gmismatch")
    raw = _invite(app, s, email="invited@x.test")

    monkeypatch.setattr(routes, "verify_google_credential", lambda cred: {
        "sub": "g-123", "email": "someoneelse@x.test", "email_verified": True,
        "name": "Wrong Person",
    })
    c = app.test_client()
    r = c.post(f"/api/invitations/accept-google/{raw}", json={"credential": "x"})
    assert r.status_code == 403
    assert r.get_json().get("mismatch") is True
    # No account may be created on mismatch.
    assert User.query.filter_by(email="invited@x.test",
                                organization_id=s["org"].id).first() is None


def test_google_accept_match_creates_user_with_invited_role(app, db, monkeypatch):
    import routes
    from models import User, Invitation
    s = _school(db, slug="gmatch")
    raw = _invite(app, s, email="invited@x.test", role="teacher")

    monkeypatch.setattr(routes, "verify_google_credential", lambda cred: {
        "sub": "g-456", "email": "invited@x.test", "email_verified": True,
        "name": "Right Person", "picture": "https://img/x.png",
    })
    c = app.test_client()
    r = c.post(f"/api/invitations/accept-google/{raw}", json={"credential": "x"})
    assert r.status_code == 201, r.get_json()
    user = User.query.filter_by(email="invited@x.test", organization_id=s["org"].id).first()
    assert user is not None
    assert user.role == "teacher"  # role comes from the invitation
    assert user.google_id == "g-456"
    assert user.password_hash is None
    assert user.profile_completed is False
    inv = Invitation.query.filter_by(organization_id=s["org"].id).first()
    assert inv.status == "accepted" and inv.accepted_at is not None
    # Token is consumed: replay must fail.
    assert c.post(f"/api/invitations/accept-google/{raw}",
                  json={"credential": "x"}).status_code in (404, 409)


def test_logout_all_devices_revokes_existing_sessions(app, db):
    s = _school(db, slug="logoutall")
    c1 = _admin_client(app, s)   # device 1
    c2 = _admin_client(app, s)   # device 2

    assert c1.get("/api/auth/me").status_code == 200
    assert c2.get("/api/auth/me").status_code == 200

    # Device 1 signs out everywhere.
    assert c1.post("/api/auth/logout-all").status_code == 200

    # Device 2's old token is now revoked.
    assert c2.get("/api/auth/me").status_code == 401
