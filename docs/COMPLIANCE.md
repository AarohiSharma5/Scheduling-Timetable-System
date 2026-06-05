# Data protection & compliance

This document describes how the platform handles personal data of students
(minors) and other users, aligned with India's **DPDP Act 2023** and the
**GDPR**. It is intended for school data-protection officers and procurement.

## 1. Data we process

| Category | Fields | Subject |
|----------|--------|---------|
| Identity | name, gender, date of birth, photo* | Student (minor) |
| Contact | address, contact number, email | Student / Parent |
| Family | father/mother name | Parent |
| Health | blood group | Student |
| Academic | class, marks, attendance, assignments | Student |
| Financial | fee invoices, payments | Student / Parent |
| Account | login email, hashed password, role | All users |
| Security | audit log (action, user, IP, timestamp) | All users |

\* Photos are not currently stored.

**Lawful basis:** performance of the school–parent contract and the school's
legitimate interest in administration. Consent is recorded per student (see §4).

## 2. Encryption at rest

Sensitive free-text PII — **father/mother name, contact number, address, blood
group** — is encrypted at the application layer with **Fernet (AES-128-CBC +
HMAC-SHA256)** before being written to the database. A leaked DB dump or disk
image therefore does not expose this data in clear.

- Key is supplied via `PII_ENCRYPTION_KEY` (never committed; see `.env.example`).
- Multiple comma-separated keys support **rotation** (first encrypts, all
  decrypt) via Fernet's `MultiFernet`.
- Ciphertext is tagged `enc::`; legacy plaintext rows remain readable and are
  migrated with a one-time backfill:

  ```bash
  docker compose exec backend flask backfill-pii-encryption
  ```

- `GET /api/health/ready` reports `pii_encryption: enabled|disabled` so you can
  verify the control is active in production.

Passwords are stored only as salted hashes (Werkzeug). Transport security (TLS)
is expected to be terminated at the reverse proxy / load balancer.

## 3. Access control & audit

- All data is tenant-isolated by `organization_id`; one school can never read
  another's records.
- Role-based access (admin, principal, teacher, student, parent) restricts who
  can see which records; class teachers are scoped to their own class.
- The `audit_logs` table records security-relevant events with user + IP +
  timestamp, including PII-sensitive actions:
  - `student.create`, `student.update`, `student.delete`
  - `pii.export` (data-subject access export)
  - `pii.anonymize` (erasure)
  - authentication events (login success/failure, lockout)

## 4. Consent

Each student record carries `consent_given`, `consent_at`, and `consent_by`
(the staff member who recorded it). Consent can be set at admission or updated
later via the student API, and is included in the data export.

## 5. Data-subject rights

| Right | How |
|-------|-----|
| Access / portability | `GET /api/admin/students/<id>/data-export` returns a full JSON bundle (profile + attendance + marks + fees + submissions). Audited as `pii.export`. |
| Erasure | `POST /api/admin/students/<id>/anonymize` irreversibly strips PII while keeping de-identified academic records for referential integrity. Audited as `pii.anonymize`. |
| Rectification | Standard student update endpoint. |

Requests are restricted to admin/principal of the owning organization.

## 6. Retention

Default retention is `DATA_RETENTION_YEARS` (7). Inactive records
(`Left`/`Inactive`/`Withdrawn`/`Graduated`) older than the window are anonymized:

```bash
docker compose exec backend flask retention-sweep          # dry run (counts only)
docker compose exec backend flask retention-sweep --apply  # anonymize
```

Schedule this monthly (cron) alongside backups.

## 7. Backups

Backups (`scripts/backup_db.sh`) inherit the same encryption: PII columns are
already ciphertext in the dump. Store dumps on encrypted storage and restrict
access. See `docs/OPERATIONS.md`.

## 8. Breach response (summary)

1. Contain (rotate `PII_ENCRYPTION_KEY`, `JWT_SECRET_KEY`, DB credentials).
2. Assess scope via `audit_logs`.
3. Notify the Data Protection Board / affected guardians as required by the
   DPDP Act timelines.

## 9. Known gaps / roadmap

- Date of birth is not yet field-encrypted (stored as a typed `DATE`).
- No automated TLS config in-repo (handled at the proxy layer).
- Photo storage, when added, must follow the same encryption + retention rules.
