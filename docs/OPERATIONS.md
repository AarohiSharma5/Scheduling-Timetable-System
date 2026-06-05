# Operations runbook

Operational guide for running this app at scale. Covers async generation,
health checks, backups, and migrations.

## Services

`docker compose` runs four services:

| Service    | Purpose                                              |
|------------|-----------------------------------------------------|
| `postgres` | Primary database (persistent volume `postgres_data`)|
| `redis`    | Rate-limit store **and** background job queue        |
| `backend`  | Gunicorn API (3 workers, 120s timeout)              |
| `worker`   | RQ worker that runs timetable generation jobs        |

## Async timetable generation

Generation is CPU-heavy and can exceed an HTTP request budget on large schools,
so it runs **off the request**:

1. `POST /api/timetable/generate` creates a draft timetable + a `generation_jobs`
   row, enqueues the job to Redis, and returns **202** with `{ job_id }`.
2. The `worker` process picks up the job and runs the scheduler.
3. The client polls `GET /api/timetable/jobs/<job_id>` until `status` is
   `completed` (result payload attached) or `failed` (error attached).

If Redis/worker is unavailable (e.g. local dev without the worker), the endpoint
**falls back to running synchronously** and returns the full result with 201, so
the feature still works everywhere.

Scale the worker horizontally:

```bash
docker compose up -d --scale worker=3
```

## Health checks

| Endpoint              | Use                                                       |
|-----------------------|-----------------------------------------------------------|
| `GET /api/health/live`| Liveness — process is up. No dependencies. Fast.          |
| `GET /api/health/ready`| Readiness — checks DB (hard) + Redis (soft). 503 if DB down.|
| `GET /api/health`     | Legacy summary with DB row counts.                        |

The compose `backend` service has a Docker healthcheck wired to `/health/live`.
Point your load balancer/orchestrator readiness probe at `/health/ready`.

## Backups

Take a compressed, timestamped dump (prunes dumps older than 14 days):

```bash
./scripts/backup_db.sh                 # writes ./backups/timetable_db_<ts>.sql.gz
BACKUP_RETENTION_DAYS=30 ./scripts/backup_db.sh /mnt/backups
```

Schedule it (example cron, daily at 02:00):

```cron
0 2 * * * cd /opt/app && ./scripts/backup_db.sh /mnt/backups >> /var/log/db-backup.log 2>&1
```

Restore (destructive — asks for confirmation):

```bash
./scripts/restore_db.sh backups/timetable_db_20260605_020000.sql.gz
docker compose exec backend flask db upgrade   # re-apply migrations if needed
```

## Database migrations

Schema changes are managed with Alembic/Flask-Migrate. Always:

```bash
docker compose exec backend flask db upgrade   # apply pending migrations
docker compose exec backend flask db current   # verify head
```

Generate a new migration after model changes:

```bash
docker compose exec backend flask db migrate -m "describe change"
# review the generated file under backend/migrations/versions/ before committing
docker compose exec backend flask db upgrade
```

Never edit an already-applied migration; add a new one instead.

## Pagination

Large list endpoints accept optional `?page=&per_page=` (max 200). When omitted,
they return the full array for backward compatibility. Example:

```
GET /api/admin/students?page=2&per_page=50
-> { "data": [...], "page": 2, "per_page": 50, "total": 2800, "pages": 56 }
```
