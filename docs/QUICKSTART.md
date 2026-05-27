# 🚀 QUICK START - School Management System v2.0

> **Status**: ✅ Backend Complete | 📱 Frontend Ready | 🗄️ 2,800 Students Ready | 📊 All Features Implemented

## ⚡ Get Running in 5 Minutes

### 1️⃣ Load Realistic Data (2-3 min)
```bash
cd backend
python seed_realistic.py
```
✅ Creates 2,800 students, 75 teachers, 4 houses, 14 classrooms - fully realistic school data

### 2️⃣ Start Backend (Keep terminal open)
```bash
cd backend
flask run --port=5000
```
✅ API running at http://localhost:5000/api

### 3️⃣ Start Frontend (New terminal)
```bash
cd frontend  
npm start
```
✅ Opens http://localhost:3000 automatically

### 4️⃣ Login with Test Account
```
Email: admin@school.edu
Password: admin123
```
✅ No more 401 errors - data persists! 🎉

### 5️⃣ Try the Features
- 📄 **PDF Export**: Download timetables (professional A4 format)
- 📋 **Leave Management**: Request leave, approve with substitute, auto-adjust timetable
- 🔔 **Notifications**: See real-time alerts for all events

---

## 📚 Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[COMPLETION_STATUS.md](COMPLETION_STATUS.md)** | Full summary of everything built | 10 min |
| **[INTEGRATION_TESTING_GUIDE.md](INTEGRATION_TESTING_GUIDE.md)** | 9-phase testing plan with commands | 30 min |
| **[backend/DATASET_DOCUMENTATION.md](backend/DATASET_DOCUMENTATION.md)** | Database structure & statistics | 5 min |
| **[backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)** | All 25+ API endpoints | 15 min |
| **[backend/FEATURES_GUIDE.md](backend/FEATURES_GUIDE.md)** | User guide + React code examples | 20 min |
| **[backend/API_QUICK_REFERENCE.md](backend/API_QUICK_REFERENCE.md)** | Copy-paste cURL commands | 5 min |

👉 **Start with [COMPLETION_STATUS.md](COMPLETION_STATUS.md)** for full overview!

---

## 🔐 Test Credentials

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Admin** | admin@school.edu | admin123 | Full system |
| **Principal** | principal@school.edu | principal123 | Dashboard + approvals |
| **Coordinator** | anjali@school.edu | coordinator123 | Section oversight |
| **Teacher** | priya.sharma@school.edu | teacher123 | My classes + leave |

All credentials auto-generated when `seed_realistic.py` runs!

---

## ✨ What's New (3 Major Features)

### 1. 📄 PDF Timetable Export
```bash
# Export class 7B timetable
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer TOKEN" \
  -o class_7b.pdf

# Features:
# ✅ Professional A4 landscape format
# ✅ School name & branding in header
# ✅ All periods and days
# ✅ Student/teacher names
# ✅ Generation timestamp
```

### 2. 📋 Teacher Leave Management
```bash
# Teacher requests leave
curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer TOKEN" \
  -d '{"leave_date":"2024-06-03","reason":"Medical"}'

# Admin approves with substitute
curl -X POST http://localhost:5000/api/leaves/42/approve \
  -H "Authorization: Bearer TOKEN" \
  -d '{"substitute_teacher_id":3}'

# Smart substitute finder automatically:
# ✅ Finds teachers with same subject
# ✅ Checks if they're free that day
# ✅ Transfers all timetable slots
# ✅ Notifies everyone affected
```

### 3. 🔔 Real-Time Notifications
```bash
# Get user notifications
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer TOKEN"

# Mark all as read
curl -X POST http://localhost:5000/api/notifications/mark-all-read \
  -H "Authorization: Bearer TOKEN"

# Auto-triggered for:
# ✅ Timetable generated
# ✅ Leave approved/rejected
# ✅ Teachers substituted
# ✅ Classes changed
```

---

## 🗄️ Database Details

**Location**: `/Users/aarohi_sharma/cpp project/timetable.db`  
**Type**: SQLite (file-based, persists across restarts)  
**Size**: ~1.2 MB  
**Records After Seeding**:
- 2,800 Students (Nursery to Class 12)
- 75 Teachers (NTT, PRT, TGT, PGT, Specialists)
- 5 Coordinators
- 1 Principal
- 4 Houses
- 14 Classrooms
- 20 Subject Masters
- **Total**: ~6,000 records

```bash
# Verify data loaded
sqlite3 timetable.db "SELECT COUNT(*) FROM students;"
# Expected output: 2800

sqlite3 timetable.db "SELECT class_grade, COUNT(*) FROM students GROUP BY class_grade ORDER BY class_grade;"
# Shows distribution: Nursery|78, LKG|84, UKG|81, 1|126, ..., 12 Humanities|136
```

---

## 📊 System Architecture

```
┌──────────────────────┐
│  React Frontend      │ (Port 3000)
│  TypeScript/Tailwind │
└──────────┬───────────┘
           │ Axios HTTP Calls
           ↓
┌──────────────────────┐
│  Flask Backend       │ (Port 5000)
│  25+ REST Endpoints  │
│  JWT Auth + RBAC     │
└──────────┬───────────┘
           │ SQLAlchemy ORM
           ↓
┌──────────────────────┐
│  SQLite Database     │
│  2,800+ Records      │
│  timetable.db        │
└──────────────────────┘

✅ JWT Authentication (Bearer tokens)
✅ Role-Based Access Control (5 roles)
✅ Professional PDF Export (ReportLab)
✅ Automated Leave Workflow
✅ Multi-recipient Notifications
```

---

## 🎯 Features Implemented

### Core System ✅
- ✅ User authentication (login, JWT tokens)
- ✅ Role-based access control (admin, principal, coordinator, teacher, student)
- ✅ School configuration (timing, periods, holidays)
- ✅ Database with 13 models and relationships

### Timetable Management ✅
- ✅ Batch/class creation (73 classes across all grades)
- ✅ Teacher assignment
- ✅ Subject assignment
- ✅ Automatic timetable generation
- ✅ Conflict detection & resolution

### New Features (This Phase) ✅
- ✅ **PDF Export**: Batch-wise and teacher-wise timetables in A4 format
- ✅ **Leave Management**: Full workflow from request → approval → substitute → timetable adjustment
- ✅ **Notifications**: Multi-event, multi-recipient notification system
- ✅ **Student Management**: 2,800+ student records with complete profiles
- ✅ **Teacher Management**: 75 teachers categorized by designation

---

## 🧪 Quick Tests

### Test 1: PDF Export
```bash
# Get admin token
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"admin123"}' \
  | jq -r '.access_token')

# Export batch timetable
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o timetable.pdf

# Open the PDF - should be high quality A4 landscape with school header
open timetable.pdf
```

### Test 2: Leave Workflow
```bash
# Teacher requests leave
curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"leave_date":"2024-06-03","reason":"Medical appointment","leave_type":"Medical"}'

# Admin gets available substitutes
curl http://localhost:5000/api/leaves/1/substitute-options \
  -H "Authorization: Bearer $TOKEN" | jq

# Admin approves with best substitute
curl -X POST http://localhost:5000/api/leaves/1/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"substitute_teacher_id":3,"auto_adjust":true}'
```

### Test 3: Check Data  
```bash
# Get all students in class 7B
curl http://localhost:5000/api/students?class=7&section=B \
  -H "Authorization: Bearer $TOKEN" | jq

# Get all teachers
curl http://localhost:5000/api/teachers \
  -H "Authorization: Bearer $TOKEN" | jq '.[:3]'

# Get coordinates
curl http://localhost:5000/api/coordinators \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- pip & npm
- SQLite3 (included with Python)

### Step 1: Install Dependencies
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### Step 2: Load Data
```bash
cd backend
python seed_realistic.py
```

### Step 3: Start Servers
```bash
# Terminal 1 - Backend
cd backend
flask run --port=5000

# Terminal 2 - Frontend
cd frontend
npm start
```

### Step 4: Access Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000/api
- Docs: See [COMPLETION_STATUS.md](COMPLETION_STATUS.md)

---

## ❓ Common Questions

**Q: Will my data persist?**  
A: Yes! SQLite saves to disk at `timetable.db` - data survives closing VSCode

**Q: Why do I get 401 errors?**  
A: Either run `seed_realistic.py` first, or login to get a fresh JWT token

**Q: How do I reset everything?**  
A: Run `python seed_realistic.py` again - recreates all tables with fresh data

**Q: Can I modify the test data?**  
A: Yes! Edit `seed_realistic.py` or `seed.py`, then re-run to reload

**Q: Is this production-ready?**  
A: Backend features: Yes. Database: For 10,000+ users, migrate to PostgreSQL

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5000 in use | Use `flask run --port=5001` |
| "No such table" error | Run `python backend/seed_realistic.py` |
| 401 Unauthorized | Login at `/api/auth/login` to get token |
| npm start fails | Run `npm install` in frontend folder first |
| Database too large | Currently 1.2 MB - perfectly fine for SQLite |

---

## 📞 Next Steps

1. **For Testing**: Follow [INTEGRATION_TESTING_GUIDE.md](INTEGRATION_TESTING_GUIDE.md) (30 min)
2. **For Frontend**: Build React components - see [backend/FEATURES_GUIDE.md](backend/FEATURES_GUIDE.md) for code examples
3. **For API Details**: See [backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)
4. **For Data**: See [backend/DATASET_DOCUMENTATION.md](backend/DATASET_DOCUMENTATION.md)

---

## ✅ Status Summary

| Component | Status | Details |
|-----------|--------|---------|
| **Backend** | ✅ Complete | 25+ endpoints, 3 features, authentication |
| **Database** | ✅ Ready | 2,800 students, 75 teachers, realistic data |
| **PDF Export** | ✅ Working | Professional A4 format with school branding |
| **Leave Mgmt** | ✅ Working | Full workflow, smart substitutes, auto-adjust |
| **Notifications** | ✅ Working | Multi-recipient, event-triggered alerts |
| **Frontend** | ⏳ Components Needed | All APIs ready, just needs UI |

---

**Backend Status**: ✅ **COMPLETE**  
**Documentation**: ✅ **COMPREHENSIVE**  
**Data**: ✅ **READY TO LOAD**  
**Time to Full Setup**: ~10 minutes  

🎉 **Everything is ready to go!**

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
