"""Shared pytest fixtures.

Each test runs against its own throwaway SQLite database so tests never touch
the real Postgres data and stay fully isolated from one another.
"""

import os
import tempfile

import pytest

# Default to the testing config before importing the app factory.
os.environ.setdefault("FLASK_ENV", "testing")

from app import create_app  # noqa: E402
from models import db as _db  # noqa: E402


@pytest.fixture()
def app():
    """A Flask app bound to a fresh, temporary SQLite file DB."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    application = create_app("testing")
    # Override the in-memory URI with a temp file so the schema/data survive
    # across the multiple connections SQLAlchemy may open during a test.
    application.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        TESTING=True,
    )

    with application.app_context():
        _db.create_all()
        try:
            yield application
        finally:
            _db.session.remove()
            _db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def db(app):
    """The SQLAlchemy handle, active within the app context."""
    return _db


@pytest.fixture()
def make_school(db):
    """Factory that builds a complete, self-contained school (organization).

    Returns a dict of the created objects so tests can assert against them:
        {org, config, subject, batch, teacher, timetable, slot}

    Every record is tagged with the same ``organization_id`` so a correctly
    tenant-scoped query returns only this school's data.
    """
    from models import (
        Organization, SchoolConfig, Subject, Batch, Teacher, User,
        Timetable, TimetableSlot,
    )

    def _make(name, slug, periods_per_day=6, working_days=5):
        org = Organization(name=name, slug=slug, password_hash="x")
        db.session.add(org)
        db.session.flush()

        config = SchoolConfig(
            organization_id=org.id,
            periods_per_day=periods_per_day,
            working_days=working_days,
        )
        db.session.add(config)

        subject = Subject(organization_id=org.id, name=f"{name} Math", periods_per_week=5)
        db.session.add(subject)
        db.session.flush()

        batch = Batch(
            organization_id=org.id, grade="9", section="A",
            student_count=30, subject_ids=[subject.id],
        )
        db.session.add(batch)
        db.session.flush()

        user = User(
            name=f"{name} Teacher", email=f"teacher@{slug}.test",
            role="teacher", organization_id=org.id,
        )
        db.session.add(user)
        db.session.flush()

        teacher = Teacher(
            organization_id=org.id, user_id=user.id, name=f"{name} Teacher",
            email=f"teacher@{slug}.test", subject_ids=[subject.id],
            assigned_batch_ids=[batch.id],
        )
        db.session.add(teacher)
        db.session.flush()

        timetable = Timetable(
            organization_id=org.id, name=f"{name} Timetable", school_name=None,
        )
        db.session.add(timetable)
        db.session.flush()

        slot = TimetableSlot(
            organization_id=org.id, timetable_id=timetable.id, day="Monday",
            period_number=1, batch_id=batch.id, teacher_id=teacher.id,
            subject_id=subject.id,
        )
        db.session.add(slot)
        db.session.commit()

        return {
            "org": org, "config": config, "subject": subject, "batch": batch,
            "teacher": teacher, "timetable": timetable, "slot": slot,
        }

    return _make
