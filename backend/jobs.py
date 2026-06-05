"""
Background job plumbing for timetable generation.

Generation can be slow on large schools, so we run it off the HTTP request.
When Redis + an RQ worker are available the request enqueues a job and returns
immediately (the client polls ``GET /api/timetable/jobs/<id>``). When they are
not (e.g. local dev, tests), the caller falls back to running synchronously.

State lives in the ``generation_jobs`` table, not worker memory, so progress is
visible from any gunicorn worker and survives a worker restart.
"""

import os
from datetime import datetime

QUEUE_NAME = "timetables"
JOB_TIMEOUT = 900  # seconds; generous for large schools


def _redis_url():
    return os.getenv("REDIS_URL") or os.getenv("RATELIMIT_STORAGE_URI")


def get_queue():
    """Return an RQ queue, or None if Redis/RQ aren't usable."""
    url = _redis_url()
    if not url:
        return None
    try:
        from redis import Redis
        from rq import Queue
        conn = Redis.from_url(url)
        conn.ping()
        return Queue(QUEUE_NAME, connection=conn)
    except Exception:
        return None


def enqueue_generation(job_id):
    """Enqueue a generation job. Returns True if it was queued to a worker."""
    queue = get_queue()
    if queue is None:
        return False
    try:
        queue.enqueue("jobs.run_generation_job", job_id, job_timeout=JOB_TIMEOUT)
        return True
    except Exception:
        return False


def run_generation_job(job_id):
    """RQ worker entrypoint: build an app context, then run the job."""
    from app import create_app
    app = create_app()
    with app.app_context():
        execute_generation(job_id)


# Kept in sync with timetable_routes; mirrored here so the worker and the
# synchronous fallback share one implementation.
DRAFT_HISTORY_LIMIT = 5


def execute_generation(job_id):
    """Run the scheduler for a job's timetable. Assumes an active app context.

    Updates the GenerationJob row to running/completed/failed and stores the
    result payload. Returns the job dict.
    """
    from models import db, GenerationJob, Timetable, TimetableSlot
    from scheduler import SchedulingEngine

    job = GenerationJob.query.get(job_id)
    if job is None:
        return None

    job.status = "running"
    job.started_at = datetime.utcnow()
    db.session.commit()

    org_id = job.organization_id
    timetable_id = job.timetable_id
    try:
        engine = SchedulingEngine(organization_id=org_id)
        success, warnings = engine.generate_timetable(timetable_id)
        if not success:
            db.session.rollback()
            job = GenerationJob.query.get(job_id)
            job.status = "failed"
            job.error = "; ".join(warnings) if warnings else "Generation failed"
            job.finished_at = datetime.utcnow()
            db.session.commit()
            return job.to_dict()

        db.session.commit()

        # Prune old drafts so storage stays bounded.
        stale = (
            Timetable.query
            .filter_by(organization_id=org_id, status="draft")
            .order_by(Timetable.generated_at.desc())
            .offset(DRAFT_HISTORY_LIMIT)
            .all()
        )
        for old in stale:
            if old.id != timetable_id:
                db.session.delete(old)
        if stale:
            db.session.commit()

        slots_count = TimetableSlot.query.filter_by(timetable_id=timetable_id).count()
        report = getattr(engine, "report", {}) or {}
        message = f"Generated {slots_count} timetable slots"
        if not report.get("complete", True):
            missing = report.get("total_required_missing", 0)
            message += f" — but {missing} required period(s) could not be placed"

        timetable = Timetable.query.get(timetable_id)
        job = GenerationJob.query.get(job_id)
        job.status = "completed"
        job.finished_at = datetime.utcnow()
        job.result = {
            "success": True,
            "timetable": timetable.to_dict() if timetable else None,
            "slots_generated": slots_count,
            "warnings": warnings,
            "report": report,
            "complete": report.get("complete", True),
            "message": message,
        }
        db.session.commit()
        return job.to_dict()

    except Exception as e:  # noqa: BLE001 - persist the failure for the client
        db.session.rollback()
        job = GenerationJob.query.get(job_id)
        if job:
            job.status = "failed"
            job.error = f"Error generating timetable: {e}"
            job.finished_at = datetime.utcnow()
            db.session.commit()
        return job.to_dict() if job else None
