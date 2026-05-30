"""Shared Flask extensions, kept in their own module to avoid circular imports.

`app.py` calls `limiter.init_app(app)` and route modules import `limiter` to
decorate individual endpoints (e.g. login throttling).
"""

import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Rate limiter. No global default limits - only explicitly decorated routes are
# throttled (currently the login endpoints, to slow brute-force attempts).
#
# Storage defaults to in-process memory. NOTE: under gunicorn with multiple
# workers, an in-memory store is per-worker, so the effective limit is roughly
# (limit x worker_count). For a shared, accurate limit in production set
# RATELIMIT_STORAGE_URI to a Redis instance, e.g. redis://redis:6379.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)
