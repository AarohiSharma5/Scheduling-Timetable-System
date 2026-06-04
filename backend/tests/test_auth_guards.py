"""Auth boundary tests via the HTTP layer.

Lock in two security guarantees from the multi-tenant work:
  * public self-registration of users is disabled (403)
  * user login is impossible without an organization session (401)
"""


def test_public_user_registration_is_blocked(app):
    client = app.test_client()
    for path in ("/api/auth/register", "/api/auth/signup"):
        resp = client.post(path, json={
            "name": "Hacker", "email": "h@x.test",
            "password": "Password123", "role": "teacher",
        })
        assert resp.status_code == 403, f"{path} should be forbidden"


def test_login_requires_organization_session(app):
    client = app.test_client()
    resp = client.post("/api/auth/login", json={
        "email": "admin@school.edu", "password": "admin123",
    })
    # No org cookie/header => org session required.
    assert resp.status_code == 401


def test_me_requires_authentication(app):
    client = app.test_client()
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


# --- Brute-force lockout + org-scoped login ---------------------------------

from werkzeug.security import generate_password_hash


def _make_org_and_user(db, *, org_slug, email, org_pw="OrgPass123", user_pw="UserPass123"):
    from models import Organization, User
    org = Organization(name=org_slug.title(), slug=org_slug,
                       password_hash=generate_password_hash(org_pw))
    db.session.add(org)
    db.session.flush()
    user = User(name="Admin", email=email, role="admin",
                organization_id=org.id, password_hash=generate_password_hash(user_pw))
    db.session.add(user)
    db.session.commit()
    return org, user


def _org_client(app, slug, org_pw="OrgPass123"):
    """A test client that has already established an organization session."""
    client = app.test_client()
    resp = client.post("/api/organizations/login",
                       json={"identifier": slug, "password": org_pw})
    assert resp.status_code == 200, resp.get_json()
    return client


def test_account_locks_after_repeated_failures(app, db):
    _make_org_and_user(db, org_slug="alpha", email="admin@alpha.test")
    client = _org_client(app, "alpha")

    # 5 wrong attempts: each rejected as invalid credentials.
    for _ in range(5):
        r = client.post("/api/auth/login",
                        json={"email": "admin@alpha.test", "password": "wrong"})
        assert r.status_code == 401

    # 6th attempt with the CORRECT password is now blocked by the lock.
    r = client.post("/api/auth/login",
                    json={"email": "admin@alpha.test", "password": "UserPass123"})
    assert r.status_code == 429
    assert r.get_json().get("locked") is True


def test_successful_login_resets_failure_counter(app, db):
    _make_org_and_user(db, org_slug="beta", email="admin@beta.test")
    client = _org_client(app, "beta")

    for _ in range(3):
        client.post("/api/auth/login",
                    json={"email": "admin@beta.test", "password": "wrong"})

    r = client.post("/api/auth/login",
                    json={"email": "admin@beta.test", "password": "UserPass123"})
    assert r.status_code == 200

    from models import User
    user = User.query.filter_by(email="admin@beta.test").first()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_login_is_scoped_to_the_org_session(app, db):
    # User lives in org "two"; we authenticate the session as org "one".
    _make_org_and_user(db, org_slug="one", email="admin@one.test")
    _make_org_and_user(db, org_slug="two", email="user@two.test")

    client = _org_client(app, "one")
    # Correct credentials, but the account isn't in the logged-in org => 401.
    r = client.post("/api/auth/login",
                    json={"email": "user@two.test", "password": "UserPass123"})
    assert r.status_code == 401


def test_same_email_allowed_in_different_orgs(app, db):
    """Two schools may each have a user with the same email; both can log in."""
    from models import User

    _make_org_and_user(db, org_slug="orga", email="shared@x.test")
    _make_org_and_user(db, org_slug="orgb", email="shared@x.test")
    assert User.query.filter_by(email="shared@x.test").count() == 2

    for slug in ("orga", "orgb"):
        client = _org_client(app, slug)
        r = client.post("/api/auth/login",
                        json={"email": "shared@x.test", "password": "UserPass123"})
        assert r.status_code == 200, f"login failed for {slug}"


def test_duplicate_email_within_one_org_is_rejected(app, db):
    """The same email twice inside ONE org must still violate uniqueness."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    from models import User

    org, _ = _make_org_and_user(db, org_slug="solo", email="dup@x.test")
    db.session.add(User(name="Dup", email="dup@x.test", role="teacher",
                        organization_id=org.id, password_hash="x"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
