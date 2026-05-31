# About the Project

**School Timetable & Management System** — a full-stack, **multi-tenant** web application that auto-generates conflict-free school timetables and manages the surrounding workflows (teachers, classes, subjects, leave, notifications) for an entire school from pre-primary through Class 12.

---

## What It Does

- **Constraint-based timetable generation** for every class (Nursery → Class 12) that respects teacher availability, subject spacing, fixed/pinned periods, and lab/double-period blocks.
- **Hours-driven scheduling** — the number of periods is derived from the configured school hours and period length, with a toggleable lunch break (or a compact, back-to-back day).
- **Per-grade day lengths** — younger grades finish earlier; editable per class or in bulk by grade.
- **Teacher leave management** with a smart substitute finder, automatic timetable adjustment, and notifications to everyone affected.
- **PDF export** of timetables in professional A4 landscape (class-wise or teacher-wise) with correct times and visible LUNCH rows.
- **Role-based dashboards** for Admin, Principal, Coordinator, Teacher, and Student.
- **Real-time notifications** for timetable changes, leave approvals, and substitutions.

---

## Tech Stack

| Layer        | Technology                              | Version |
| ------------ | --------------------------------------- | ------- |
| Frontend     | React + TypeScript                      | 18.2    |
| State        | Zustand                                 | 4.4     |
| Styling      | Tailwind CSS                            | 3.3     |
| HTTP         | Axios (cookie auth, `withCredentials`)  | 1.5     |
| Routing      | React Router                            | 6.14    |
| Backend      | Flask (app factory + blueprints)        | 2.3     |
| ORM          | Flask-SQLAlchemy                        | 3.0     |
| Migrations   | Flask-Migrate (Alembic)                 | 4.0     |
| Rate limit   | Flask-Limiter + Redis                   | 3.5     |
| Auth         | PyJWT via **httpOnly cookies**          | 2.13    |
| PDF          | ReportLab                               | 4.0     |
| Database     | PostgreSQL (prod) / SQLite (dev)        | —       |
| App server   | gunicorn                                | 21.2    |
| Container    | Docker + docker-compose                 | —       |

---

## Architecture

```
┌───────────────────────────┐
│  React + TypeScript SPA    │  served as static build
│  Tailwind · Zustand        │
└─────────────┬──────────────┘
              │ Axios (httpOnly cookie auth: org_token + access_token)
              ▼
┌───────────────────────────┐
│  Flask REST API (gunicorn) │  Port 3000
│  RBAC · per-org scoping    │
│  Flask-Limiter ──► Redis   │
└─────────────┬──────────────┘
              │ SQLAlchemy + Alembic migrations
              ▼
┌───────────────────────────┐
│  PostgreSQL (prod)         │
│  SQLite (local dev)        │
└───────────────────────────┘
```

- **Two-step authentication**: organization login (`POST /api/organizations/login`) sets an `org_token` cookie, then user login (`POST /api/auth/login`) sets an `access_token` cookie. Both are **httpOnly**, so no token is ever exposed to JavaScript (mitigates XSS token theft).
- **Authorization**: role-based access control (admin, principal, coordinator, teacher, student).
- **Multi-tenancy**: every model carries an `organization_id`; all queries are scoped per organization so multiple institutions can share one deployment safely.
- **Persistence**: PostgreSQL in production; SQLite for local development. Schema changes are versioned with Alembic migrations.

---

## Project Structure

```
cpp project/
├── backend/                  # Flask API
│   ├── app.py                # App factory, CORS (credentials), blueprints, security headers
│   ├── wsgi.py               # gunicorn entrypoint (wsgi:app)
│   ├── config.py             # Environment config + secret resolution
│   ├── extensions.py         # Shared extensions (Limiter, Migrate)
│   ├── models.py             # SQLAlchemy models (Organization, Users, Batches, Teachers, …, PinnedSlot)
│   ├── routes.py             # Main REST endpoints (auth, admin CRUD, config, exports)
│   ├── timetable_routes.py   # Timetable generation, listing, publish, validation
│   ├── scheduler.py          # Constraint-based generation engine (SchedulingEngine)
│   ├── period_utils.py       # Shared period/lunch/day-length math (engine + PDF)
│   ├── conflict_detector.py  # Conflict validation rules
│   ├── leave_service.py      # Leave + substitute workflow
│   ├── pdf_utils.py          # PDF export (ReportLab)
│   ├── jwt_utils.py          # JWT encode/decode (cookies) + RBAC decorators
│   ├── seed_realistic.py     # Full demo dataset (~2,800 students, 75 teachers)
│   ├── migrations/           # Alembic schema versions
│   ├── requirements.txt
│   └── Dockerfile            # gunicorn-served image
├── frontend/                 # React + TypeScript SPA
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── documentation/            # Project docs (this folder)
│   ├── ABOUT.md
│   ├── SETUP.md
│   └── API.md
├── docker-compose.yml        # postgres + redis + backend
├── .env.example              # Required secrets (JWT_SECRET_KEY, SECRET_KEY, …)
└── …
```

---

## Core Features

### Timetable Engine (`scheduler.py`)
Generates per-class, per-day, per-period assignments while enforcing:
- **Teacher conflicts** — a teacher is never double-booked, and weekly load limits are respected.
- **Batch conflicts** — a class never has two subjects in the same slot.
- **Teacher availability** — admin-defined blocked slots are never used.
- **Subject spacing** — `max_periods_per_day` (default 1) prevents same-subject repeats / back-to-back.
- **Fixed / pinned periods** — admin-locked slots are placed first, everything else schedules around them.
- **Lab / double periods** — subjects flagged `requires_double` are placed as consecutive pairs (one block per day).
- **Hours & lunch** — period count is derived from school hours ÷ period length; lunch is one optional, visible period.
- **Per-grade day length** — each class's `periods_per_day` lets juniors finish earlier than seniors.

Generation is **versioned**: each run creates a new draft; the **5 most recent drafts** are kept as rolling history (older drafts and their slots are pruned), while **published** timetables are preserved permanently — keeping storage bounded.

### Conflict Detection (`conflict_detector.py`)
Runs against a timetable and reports **errors** (double-booking) and **warnings** (subject gaps, uneven distribution) before publishing.

### Leave Workflow (`leave_service.py`)
1. Teacher submits a leave request.
2. Admin/Principal views pending leaves and finds available substitutes who teach the same subject and are free.
3. On approval, affected slots are reassigned and notifications are dispatched to everyone affected.

### Notifications
Auto-triggered on timetable changes, leave approval/rejection, and substitutions. Per-user inbox with unread counts, mark-read, and delete.

### PDF Export (`pdf_utils.py`)
A4 landscape with the organization name, generation timestamp, correct period times, and visible LUNCH rows. Export class-wise (one class per page) or teacher-wise (one teacher per page), all or a single item.

---

## Seeded Dataset (after `python seed_realistic.py`)

| Entity                 | Count   |
| ---------------------- | ------- |
| Students               | ~2,800  |
| Teachers               | 75      |
| Coordinators           | 5       |
| Principal              | 1       |
| Batches / Sections     | 59      |
| Houses                 | 4       |
| Classrooms             | 14      |
| Subjects               | 25      |

Includes realistic roll numbers, admission numbers, and teacher codes, plus sample teacher availability and a pinned period to demonstrate the scheduling constraints.

**Demo login** — Organization: `test-sample-institute` / `institute123`, then Admin: `admin@school.edu` / `admin123`.

See [`SETUP.md`](./SETUP.md) for installation and [`API.md`](./API.md) for the full endpoint reference.
