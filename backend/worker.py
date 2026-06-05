"""
RQ worker entrypoint for background jobs (timetable generation).

Run with:  python worker.py
or:        rq worker -u $REDIS_URL timetables

Each enqueued task builds its own Flask app context (see jobs.run_generation_job),
so the worker process only needs Redis connectivity.
"""

import os
import sys

from redis import Redis
from rq import Queue, Worker

from jobs import QUEUE_NAME, _redis_url


def main():
    url = _redis_url()
    if not url:
        print("REDIS_URL (or RATELIMIT_STORAGE_URI) is not set; cannot start worker.", file=sys.stderr)
        sys.exit(1)
    conn = Redis.from_url(url)
    worker = Worker([Queue(QUEUE_NAME, connection=conn)], connection=conn)
    print(f"[worker] listening on '{QUEUE_NAME}' via {url}")
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
