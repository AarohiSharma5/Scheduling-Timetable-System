"""Vercel serverless entry point for the Flask backend.

Vercel's Python runtime serves the module-level ``app`` (a WSGI app) for every
request routed here (see vercel.json -> ``/api/(.*)``). The actual application
code lives in ../backend, so we put that on the import path first.

Caveat: serverless functions are short-lived and time-limited. Heavy timetable
generation can exceed Vercel's function timeout; the rest of the app (auth, data
management, viewing existing timetables) works fine.
"""

import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

# Force production config: enables ProxyFix (so HTTPS is detected behind Vercel's
# proxy and the auth cookies' Secure flag turns on) and the strong-secret checks.
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app  # noqa: E402

app = create_app("production")
