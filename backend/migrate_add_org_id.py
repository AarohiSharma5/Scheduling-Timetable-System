"""In-place migration: add organization_id to tenant tables and backfill.

Why this exists
---------------
We introduced real multi-tenancy by adding an ``organization_id`` column to the
core data models. SQLAlchemy's ``db.create_all()`` only creates *missing*
tables - it never ALTERs an existing one - so a database that already holds
data (like the seeded demo) would be missing the new column.

This script is the non-destructive alternative to dropping the volume:
  1. Ensure an Organization row exists (the demo "Test Sample Institute").
  2. ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS organization_id`` on each table.
  3. Backfill every pre-existing row with that organization's id.

It is idempotent - safe to run multiple times - and preserves all data.

Usage:
    python migrate_add_org_id.py
"""

from app import create_app
from models import db, Organization
from sqlalchemy import text
from werkzeug.security import generate_password_hash

# Tables that gained an organization_id column.
TENANT_TABLES = [
    "users",
    "teachers",
    "students",
    "batches",
    "subjects",
    "school_config",
    "timetables",
    "timetable_slots",
    "leave_requests",
]

DEFAULT_ORG_NAME = "Test Sample Institute"
DEFAULT_ORG_SLUG = "test-sample-institute"
DEFAULT_ORG_PASSWORD = "institute123"


def run():
    app = create_app()
    with app.app_context():
        # Make sure the organizations table (and any brand-new tables) exist.
        db.create_all()

        org = Organization.query.order_by(Organization.id).first()
        if not org:
            org = Organization(
                name=DEFAULT_ORG_NAME,
                slug=DEFAULT_ORG_SLUG,
                password_hash=generate_password_hash(DEFAULT_ORG_PASSWORD),
                description="Demo institute.",
                logo_url="/scheduler-logo.png",
            )
            db.session.add(org)
            db.session.commit()
            print(f"Created organization '{org.name}' (id={org.id})")
        org_id = org.id
        print(f"Backfilling all tenant rows to organization_id={org_id} ({org.name})")

        # 1. Add the column where missing (Postgres supports IF NOT EXISTS).
        for table in TENANT_TABLES:
            db.session.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS organization_id INTEGER")
            )
        db.session.commit()

        # 2. Backfill existing rows that predate the column.
        for table in TENANT_TABLES:
            result = db.session.execute(
                text(f"UPDATE {table} SET organization_id = :oid WHERE organization_id IS NULL"),
                {"oid": org_id},
            )
            print(f"  {table}: backfilled {result.rowcount} row(s)")
        db.session.commit()

        print("Migration complete. No data was dropped.")


if __name__ == "__main__":
    run()
