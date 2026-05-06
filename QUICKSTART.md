# Quick Start Guide

## 30-Second Setup

### Prerequisites
- Python 3.11+ and pip
- Node.js 18+ and npm
- SQLite (included with Python)

### Option 1: Local Development (Fastest)

```bash
# Terminal 1: Start Backend
cd backend
pip install -r requirements.txt
export DATABASE_URL="sqlite:///timetable.db"
python -m flask run --port=5000

# Terminal 2: Start Frontend
cd frontend
npm install
npm start
```

**Open browser:** http://localhost:3000

---

### Option 2: Docker Compose (Recommended for Production)

```bash
docker-compose up
```

**Open browser:** http://localhost:3000

Backend API: http://localhost:5000/api
PostgreSQL: localhost:5432 (credentials in docker-compose.yml)

---

## First Steps

1. **Create a Plan** - Click "Create Plan" on dashboard
2. **Setup Institution** - Configure school parameters (days, periods, teachers capacity)
3. **Add Curriculum** - Add teachers and subjects
4. **Generate Timetable** - System schedules classes automatically
5. **Export CSV** - Download for use in your school

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript | 18.2 |
| State | Zustand | 4.4 |
| Styling | Tailwind CSS | 3.3 |
| Backend | Flask | 2.3 |
| Database | SQLite (dev) / PostgreSQL (prod) | - |
| Container | Docker | - |

---

## Troubleshooting

**Backend won't start:**
```bash
rm backend/timetable.db  # Reset database
pip install --upgrade -r backend/requirements.txt
```

**Frontend won't compile:**
```bash
rm -rf frontend/node_modules frontend/package-lock.json
npm install
```

**Port conflicts:**
Edit port mappings in backend/app.py or frontend/.env

---

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/plans` - Create plan
- `GET /api/plans` - List plans
- `GET /api/plans/:id` - Get plan
- `POST /api/plans/:id/generate` - Generate timetable
- `GET /api/plans/:id/export/csv` - Export CSV

---

## Documentation

- [Full Stack Summary](./FULLSTACK_SUMMARY.md) - Feature overview
- [Conversion Details](./CONVERSION_DETAILS.md) - C++ to Python/React
- [Deployment Checklist](./CHECKLIST.md) - Production readiness
