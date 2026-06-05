"""Tests for PII encryption at rest, consent, audit, and data-subject rights."""

import os

import pytest
from werkzeug.security import generate_password_hash


# --------------------------------------------------------------------------- helpers

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


def _add_student(client, **extra):
    payload = {"first_name": "Asha", "last_name": "Rao", "class_grade": "9",
               "section": "A", "contact_number": "9876543210",
               "address": "12 Main St", "blood_group": "B+",
               "father_name": "Ravi Rao"}
    payload.update(extra)
    r = client.post("/api/admin/students", json=payload)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


@pytest.fixture
def encryption_on():
    from cryptography.fernet import Fernet
    import crypto_utils
    key = Fernet.generate_key().decode()
    old = os.environ.get("PII_ENCRYPTION_KEY")
    os.environ["PII_ENCRYPTION_KEY"] = key
    crypto_utils.reload_encryption()
    yield
    if old is None:
        os.environ.pop("PII_ENCRYPTION_KEY", None)
    else:
        os.environ["PII_ENCRYPTION_KEY"] = old
    crypto_utils.reload_encryption()


# --------------------------------------------------------------------------- crypto unit

def test_encrypt_roundtrip_and_prefix(encryption_on):
    from crypto_utils import encrypt_value, decrypt_value, is_encrypted
    token = encrypt_value("9876543210")
    assert is_encrypted(token)
    assert token != "9876543210"
    assert decrypt_value(token) == "9876543210"


def test_decrypt_tolerates_legacy_plaintext(encryption_on):
    from crypto_utils import decrypt_value
    assert decrypt_value("plain-legacy-value") == "plain-legacy-value"


def test_passthrough_when_no_key():
    import crypto_utils
    crypto_utils.reload_encryption()  # no key in env
    assert crypto_utils.encryption_enabled() is False
    assert crypto_utils.encrypt_value("x") == "x"


# --------------------------------------------------------------------------- column encryption

def test_pii_stored_as_ciphertext(app, db, encryption_on):
    s = _school(db, slug="encco")
    admin = _admin_client(app, s)
    created = _add_student(admin)

    # ORM read decrypts transparently.
    assert created["contact_number"] == "9876543210"

    # Raw column read (bypasses the type decorator) must be ciphertext.
    raw = db.session.execute(
        db.text("SELECT contact_number, address FROM students WHERE id=:i"),
        {"i": created["id"]},
    ).first()
    assert raw[0].startswith("enc::")
    assert "9876543210" not in raw[0]
    assert raw[1].startswith("enc::")


# --------------------------------------------------------------------------- consent

def test_consent_recorded(app, db):
    s = _school(db, slug="consentco")
    admin = _admin_client(app, s)
    created = _add_student(admin, consent_given=True)
    assert created["consent_given"] is True
    assert created["consent_at"] is not None


def test_consent_defaults_false(app, db):
    s = _school(db, slug="consentco2")
    admin = _admin_client(app, s)
    created = _add_student(admin)
    assert created["consent_given"] is False


# --------------------------------------------------------------------------- data-subject rights

def test_data_export_bundle_and_audit(app, db):
    from models import AuditLog
    s = _school(db, slug="dsrexport")
    admin = _admin_client(app, s)
    created = _add_student(admin)

    r = admin.get(f"/api/admin/students/{created['id']}/data-export")
    assert r.status_code == 200
    bundle = r.get_json()
    assert bundle["profile"]["student_id"] == created["student_id"]
    assert "attendance" in bundle["records"]
    assert "counts" in bundle

    logged = AuditLog.query.filter_by(organization_id=s["org"].id, action="pii.export").first()
    assert logged is not None
    assert logged.detail.get("student_id") == created["student_id"]


def test_anonymize_strips_pii_and_audits(app, db):
    from models import AuditLog, Student
    s = _school(db, slug="dsrerase")
    admin = _admin_client(app, s)
    created = _add_student(admin)

    r = admin.post(f"/api/admin/students/{created['id']}/anonymize")
    assert r.status_code == 200

    student = Student.query.get(created["id"])
    assert student.status == "Anonymized"
    assert student.contact_number is None
    assert student.father_name is None
    assert student.address is None
    assert student.first_name == "Redacted"
    # student_id retained for referential integrity.
    assert student.student_id == created["student_id"]

    logged = AuditLog.query.filter_by(organization_id=s["org"].id, action="pii.anonymize").first()
    assert logged is not None


def test_dsr_is_tenant_scoped(app, db):
    a = _school(db, slug="dsrta")
    b = _school(db, slug="dsrtb")
    created = _add_student(_admin_client(app, a))
    cb = _admin_client(app, b)
    assert cb.get(f"/api/admin/students/{created['id']}/data-export").status_code == 404
    assert cb.post(f"/api/admin/students/{created['id']}/anonymize").status_code == 404
