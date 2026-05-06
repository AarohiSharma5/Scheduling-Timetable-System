# 🎉 Full-Stack Timetable Planner

## Welcome! Start Here

Your professional full-stack timetable planning application is ready to run.

### 🚀 Quick Start (Choose One)

**Option 1: Docker (Easiest - Recommended)**
```bash
docker-compose up -d
```
Then open: **http://localhost:3000**

**Option 2: Local Development**
```bash
# Terminal 1 - Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite:///timetable.db"
flask run --port=5000

# Terminal 2 - Frontend
cd frontend && npm install && npm start
```
Then open: **http://localhost:3000**

### 📚 Documentation
- **README.md** - Full reference and features
- **backend/** - Flask REST API (Python)
- **frontend/** - React app (TypeScript)

### ✨ Features
- ✅ Create & manage timetable plans
- ✅ Multi-step workflow (Setup → Curriculum → Review)
- ✅ Automatic scheduling algorithm
- ✅ Export to CSV
- ✅ Persistent database (PostgreSQL/SQLite)
- ✅ Production-ready deployment

Happy planning! 📅
