# 🔧 Troubleshooting: 401 Unauthorized Error (Data Not Persisting)

## Problem Summary

You're getting a **401 Unauthorized** error every time you close and reopen Visual Studio Code. This happens because:

1. Frontend stores auth token in `localStorage`
2. When you restart, token is still there
3. But backend's database is empty → user doesn't exist → `/auth/me` returns 401
4. frontend clears token and redirects to login

---

## Root Cause: Missing Database Initialization

### 📍 Where Your Database Is Located

```
/Users/aarohi_sharma/cpp project/timetable.db
```

**Defined in**: `backend/config.py` line 13
```python
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///timetable.db")
```

**How it works**:
- SQLite file-based database (not in-memory)
- **Should** persist data between restarts ✅
- **But** requires test data to be seeded first ⚠️

---

## ✅ Solution: Always Seed Before Starting

### Option 1: Quick Start (One Command)

```bash
cd backend
bash run.sh
```

This script will:
1. Install dependencies (if needed)
2. **Seed database** with test data
3. Start Flask server

### Option 2: Manual Steps

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt

# Seed the database
python seed.py

# Start the server
export DATABASE_URL="sqlite:///timetable.db"
python -m flask run --port=5000
```

```bash
# Terminal 2: Frontend
cd frontend
npm install
npm start
```

---

## 🎯 Test Credentials (After Seeding)

After running `python seed.py`, use these to login:

| Role | Email | Password |
|------|-------|----------|
| **Admin** | `admin@school.edu` | `admin123` |
| **Principal** | `principal@school.edu` | `principal123` |
| **Teacher** | `teacher1@school.edu` | `teacher123` |
| **Student** | `student1@school.edu` | `student123` |

---

## 📊 How Data Storage Works

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (React)                       │
│  localStorage: { auth_token: "jwt_..." }               │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP + Bearer Token
                   ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND (Flask + SQLAlchemy)               │
│  ┌──────────────────────────────────────────────────┐  │
│  │ JWT Verification (jwt_utils.py)                  │  │
│  │ ✓ Validates token signature                      │  │
│  │ ✗ Returns 401 if token invalid/expired           │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Database Query (models.py)                       │  │
│  │ SELECT * FROM users WHERE id=token.user_id      │  │
│  │ ✗ Returns 401 if user not found in DB            │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                DATABASE (SQLite)                        │
│  File: /Users/aarohi_sharma/cpp project/timetable.db  │
│                                                         │
│  Tables:                                                │
│  • users (email, password_hash, role)                   │
│  • teachers                                             │
│  • batches (grades/sections)                            │
│  • subjects                                             │
│  • timetables                                           │
│  • timetable_slots                                      │
│  • school_config                                        │
└─────────────────────────────────────────────────────────┘
```

### Why 401 Occurs

```
Scenario 1: Database is EMPTY
├─ Frontend has token in localStorage ✓
├─ Token signature is valid ✓
├─ But User record missing from DB ✗
└─ Result: 401 UNAUTHORIZED 🔴

Scenario 2: After Seeding
├─ Frontend has token in localStorage ✓
├─ Token signature is valid ✓
├─ User record exists in DB ✓
└─ Result: 200 OK ✅
```

---

## 🐛 Check Your Database Status

### View SQLite Database

```bash
# List all records in users table
sqlite3 "/Users/aarohi_sharma/cpp project/timetable.db"
sqlite> SELECT id, name, email, role FROM users;
```

### Expected Output After Seeding
```
1|Admin User|admin@school.edu|admin
2|Principal|principal@school.edu|principal
3|Teacher 1|teacher1@school.edu|teacher
4|Student 1|student1@school.edu|student
...
```

### Expected Output Before Seeding
```
(empty database)
```

---

## Code Reference: How Seeding Works

### `backend/seed.py`
```python
def seed_database():
    # 1. Drop all existing data
    db.drop_all()
    
    # 2. Create fresh tables
    db.create_all()
    
    # 3. Add test users
    admin = User(
        name="Admin User",
        email="admin@school.edu",
        password_hash=generate_password_hash("admin123"),  # Hashed!
        role="admin"
    )
    db.session.add(admin)
    db.session.commit()  # ← Data persisted to timetable.db
```

---

## How Data Loads on Backend Restart

```
Backend startup:
├─ 1. Read config → DATABASE_URL="sqlite:///timetable.db"
├─ 2. Open timetable.db file
├─ 3. Load existing tables and data
├─ 4. Backend is ready to handle requests
└─ User data persists across restarts ✓
```

---

## Recommended Workflow

### First Time Setup
```bash
/Users/aarohi_sharma/cpp project/
├─ Terminal 1: cd backend && bash run.sh
│  └─ Runs seed.py automatically
├─ Terminal 2: cd frontend && npm start
└─ Open http://localhost:3000
   Use: principal@school.edu / principal123
```

### Subsequent Starts (Next Day)
```bash
# Database is already seeded, just start:
cd backend && python -m flask run --port=5000
cd frontend && npm start
```

### If You Need Fresh Data
```bash
cd backend
python seed.py  # Wipes and reseeds
python -m flask run --port=5000
```

---

## Key Takeaways

✅ **Database File**: `timetable.db` (persists to disk)
✅ **Auth Flow**: Login → Token in localStorage → Sent with each request
✅ **401 Error**: Always means user doesn't exist in DB
✅ **Solution**: Run `python seed.py` before starting backend
✅ **Data Sync**: Data stays in database file even after restart

---

## Still Having Issues?

Run this diagnostic:

```bash
# Check if database file exists
ls -lh "/Users/aarohi_sharma/cpp project/timetable.db"

# Check if it has data
sqlite3 "/Users/aarohi_sharma/cpp project/timetable.db" "SELECT COUNT(*) as user_count FROM users;"

# Check backend logs
python -m flask run --port=5000
# Look for: "db_stats": {"users": 8, ...}
```

If user_count = 0, run: `python seed.py`
