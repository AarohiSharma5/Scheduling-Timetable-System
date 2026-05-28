# About the Project

**School Management & Timetable System** — a full‑stack web application for generating, validating, and managing school timetables, teacher leave workflows, and real‑time notifications for a multi‑grade school.

---

## What It Does

- **Automated timetable generation** for all batches (Nursery → Class 12) with conflict detection (teacher double-booking, batch double-booking, subject gaps).
- **Teacher leave management** with smart substitute finder, automatic timetable adjustment, and notifications to everyone affected.
- **PDF export** of timetables in professional A4 landscape (batch-wise or teacher-wise).
- **Role-based dashboards** for Admin, Principal, Coordinator, Teacher, and Student.
- **Real-time notifications** for timetable changes, leave approvals, and substitutions.

---

## Tech Stack

| Layer        | Technology                       | Version |
| ------------ | -------------------------------- | ------- |
| Frontend     | React + TypeScript               | 18.2    |
| State        | Zustand                          | 4.4     |
| Styling      | Tailwind CSS                     | 3.3     |
| HTTP         | Axios                            | 1.5     |
| Routing      | React Router                     | 6.14    |
| Backend      | Flask                            | 2.3     |
| ORM          | Flask-SQLAlchemy                 | 3.0     |
| Auth         | PyJWT (JWT bearer tokens)        | 2.13    |
| PDF          | ReportLab + WeasyPrint           | 4.0 / 60|
| Database     | SQLite (dev) / PostgreSQL (prod) | —       |
| Container    | Docker + docker-compose          | —       |

---

## Architecture

```
┌──────────────────────┐
│  React Frontend      │ Port 3000
│  TypeScript / Tailwind│
└──────────┬───────────┘
           │ Axios (JWT bearer)
           ▼
┌──────────────────────┐
│  Flask Backend       │ Port 5000
│  REST API + RBAC     │
└──────────┬───────────┘
           │ SQLAlchemy
           ▼
┌──────────────────────┐
│  SQLite / PostgreSQL │
│  timetable.db        │
└──────────────────────┘
```

- **Authentication**: JWT bearer tokens, returned by `POST /api/auth/login`.
- **Authorization**: Role-based access control (admin, principal, coordinator, teacher, student).
- **Persistence**: SQLite file (`timetable.db`) for development; PostgreSQL supported for production via `psycopg2`.

---

## Project Structure

```
cpp project/
├── backend/                # Flask API
│   ├── app.py              # App factory + CORS + blueprint registration
│   ├── config.py           # Environment config
│   ├── models.py           # SQLAlchemy models (Users, Batches, Teachers, …)
│   ├── routes.py           # Main REST endpoints
│   ├── timetable_routes.py # Timetable generation + validation endpoints
│   ├── planner_service.py  # Timetable generation logic
│   ├── conflict_detector.py# Conflict validation rules
│   ├── leave_service.py    # Leave + substitute workflow
│   ├── pdf_utils.py        # PDF export (ReportLab)
│   ├── jwt_utils.py        # JWT encode/decode + decorators
│   ├── seed.py             # Minimal seed data
│   ├── seed_realistic.py   # Full dataset (2,800 students, 75 teachers)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React + TypeScript SPA
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── documentation/          # Project docs (this folder)
│   ├── ABOUT.md
│   ├── SETUP.md
│   └── API.md
├── docker-compose.yml
└── timetable.db            # SQLite database (created after seeding)
```

---

## Core Features

### Timetable Engine
- Generates per-batch, per-day, per-period assignments respecting school hours, lunch breaks, and subject distribution rules.
- **Conflict detector** runs after generation and surfaces:
  - **Errors**: teacher double-booked, classroom/batch double-booked.
  - **Warnings**: subject gaps, uneven distribution.
- Timetables can be reviewed, regenerated, then **published**.

### Leave Workflow
1. Teacher submits a leave request (`POST /api/leaves/request`).
2. Admin/Principal views pending leaves and queries `substitute-options` to find available teachers with the same subject.
3. On approval, affected timetable slots are reassigned to the substitute and notifications are dispatched.

### Notifications
- Auto-triggered on: timetable generation, leave approval/rejection, teacher substitution, classroom changes.
- Per-user inbox: list, unread count, mark read / mark-all-read, delete.

### PDF Export
- A4 landscape, school header, generation timestamp.
- Batch view (one batch per page) or teacher view (one teacher per page).

---

## Seeded Dataset (after `seed_realistic.py`)

| Entity        | Count   |
| ------------- | ------- |
| Students      | 2,800   |
| Teachers      | 75      |
| Coordinators  | 5       |
| Principal     | 1       |
| Houses        | 4       |
| Classrooms    | 14      |
| Subjects      | 20      |
| **Total rows**| ~6,000  |

See [`SETUP.md`](./SETUP.md) for installation and [`API.md`](./API.md) for the full endpoint reference.
