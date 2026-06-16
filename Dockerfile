# Production image: builds the React frontend, then serves it together with the
# Flask API from a single container (same origin -> no CORS to configure).
#
# Works on Render, Railway, Fly.io, or any plain Docker host. The background
# worker runs from this SAME image, just with a different start command
# (`python worker.py`), so both stay perfectly in sync.

# ---- Stage 1: build the React app ----
FROM node:18-alpine AS frontend
WORKDIR /frontend
# CRA treats lint warnings as errors when CI is set; don't fail the build on them.
ENV CI=false
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: python runtime serving API + built frontend ----
FROM python:3.11-slim
WORKDIR /app

# System deps kept minimal; psycopg2-binary needs no build toolchain.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend code lives at /app; app.py expects the built frontend at ../frontend/build.
COPY backend/ /app/
COPY --from=frontend /frontend/build /frontend/build

# Startup script: runs DB migrations then the main process (see entrypoint.sh).
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV FLASK_ENV=production
# Lets `flask db upgrade` (run from entrypoint.sh) find the app deterministically.
ENV FLASK_APP=wsgi:app
EXPOSE 3000

# entrypoint.sh migrates the DB, then execs this command. 2 workers keeps memory
# within the free 512 MB tier; generation can be slow so allow a long timeout.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--workers", "2", "--timeout", "120", "--bind", "0.0.0.0:3000", "wsgi:app"]
