"""
Operational CLI commands (run via `flask <command>` inside the backend container).

  flask backfill-pii-encryption   one-time: encrypt existing plaintext PII rows
  flask retention-sweep [--apply]  anonymize records past the retention window
"""

import os
from datetime import datetime, timedelta

import click
from flask.cli import with_appcontext


# Encrypted PII columns to re-save during backfill.
_ENCRYPTED_FIELDS = ("father_name", "mother_name", "contact_number", "address", "blood_group")


def register_cli(app):
    @app.cli.command("backfill-pii-encryption")
    @with_appcontext
    def backfill_pii_encryption():
        """Re-save every student so plaintext PII becomes encrypted at rest."""
        from models import db, Student
        from crypto_utils import encryption_enabled
        from sqlalchemy.orm.attributes import flag_modified

        if not encryption_enabled():
            click.echo("PII_ENCRYPTION_KEY is not set — nothing to encrypt. Aborting.")
            return

        count = 0
        for student in Student.query.yield_per(200):
            touched = False
            for field in _ENCRYPTED_FIELDS:
                if getattr(student, field) is not None:
                    flag_modified(student, field)
                    touched = True
            if touched:
                count += 1
        db.session.commit()
        click.echo(f"Encrypted PII for {count} student record(s).")

    @app.cli.command("retention-sweep")
    @click.option("--apply", "do_apply", is_flag=True,
                  help="Actually anonymize. Without this flag it's a dry run.")
    @with_appcontext
    def retention_sweep(do_apply):
        """Anonymize inactive students past DATA_RETENTION_YEARS (default 7)."""
        from models import db, Student
        from compliance_utils import anonymize_student

        years = int(os.getenv("DATA_RETENTION_YEARS", "7"))
        cutoff = datetime.utcnow() - timedelta(days=365 * years)
        candidates = (
            Student.query
            .filter(Student.status.in_(["Left", "Inactive", "Withdrawn", "Graduated"]))
            .filter(Student.updated_at < cutoff)
            .all()
        )
        click.echo(f"{len(candidates)} record(s) inactive and older than {years} year(s).")
        if not do_apply:
            click.echo("Dry run — re-run with --apply to anonymize them.")
            return
        for student in candidates:
            anonymize_student(student)
        db.session.commit()
        click.echo(f"Anonymized {len(candidates)} record(s).")
