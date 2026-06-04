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
