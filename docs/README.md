# Timetable Planning Studio - Full Stack Application

## 🎯 Overview

A modern, professional timetable planning system with:
- **Python/Flask REST API** - Robust backend with PostgreSQL
- **React + TypeScript** - Modern, responsive frontend 
- **Real-time Collaboration** - WebSocket support via Socket.IO
- **Docker Support** - One-command deployment
- **Advanced Scheduling** - Load-balancing algorithm for optimal timetable generation

## 📁 Project Structure

```
├── backend/                 # Flask API server
│   ├── app.py              # Application factory
│   ├── config.py           # Configuration management
│   ├── models.py           # SQLAlchemy database models
│   ├── routes.py           # API endpoints
│   ├── planner_service.py  # Business logic (ported from C++)
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend container
│   └── .env.example        # Environment variables template
│
├── frontend/               # React + TypeScript app
│   ├── src/
│   │   ├── api.ts          # API client
│   │   ├── types.ts        # TypeScript types
│   │   ├── store.ts        # Zustand state management
│   │   ├── App.tsx         # Main app component
│   │   ├── pages/          # Page components
│   │   │   ├── DashboardPage.tsx  # Plan list
│   │   │   ├── SetupPage.tsx      # Step 1: Institution setup
│   │   │   ├── CurriculumPage.tsx # Step 2: Teachers & subjects
│   │   │   └── ReviewPage.tsx     # Step 3: Timetable view
│   │   ├── components/     # Reusable components
│   │   │   ├── Common.tsx        # Header, footer, alerts
│   │   │   ├── SetupForm.tsx     # Institution form
│   │   │   ├── CurriculumEditor.tsx # Teacher/subject editor
│   │   │   └── TimetableReview.tsx  # Timetable display
│   │   ├── index.tsx       # React entry point
│   │   └── index.css       # Tailwind styles
│   ├── public/
│   │   └── index.html      # HTML template
│   ├── package.json        # Node dependencies
│   ├── tsconfig.json       # TypeScript config
│   ├── tailwind.config.js  # Tailwind CSS config
│   ├── postcss.config.js   # PostCSS config
│   ├── Dockerfile          # Frontend container
│   └── .env.example        # Environment variables
│
├── docker-compose.yml      # Docker orchestration
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- Or: Node.js 18+, Python 3.11+, PostgreSQL 15+

### Option 1: Docker (Recommended)

```bash
# Clone the project
cd /Users/aarohi_sharma/cpp\ project

# Create environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# API: http://localhost:5000/api
# Database: localhost:5432
```

### Option 2: Local Development

**Backend:**
```bash
cd backend

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and set DATABASE_URL

# Run Flask app
flask run  # Starts on http://localhost:5000
```

**Frontend:**
```bash
cd frontend

# Install Node dependencies
npm install

# Start development server
npm start  # Starts on http://localhost:3000
```

## 🔑 Features

### 📊 Three-Step Planning Workflow

1. **Institution Setup** (`/setup`)
   - Define school parameters (days/week, periods/day, student count)
   - Set core/elective subject targets
   - Create initial plan

2. **Curriculum Configuration** (`/plans/:id/curriculum`)
   - Add/edit teachers with contact hours
   - Add/edit subjects with teacher assignments
   - Configure period requirements
   - Mark subjects as core or elective

3. **Timetable Review** (`/plans/:id/review`)
   - View auto-generated timetable grid
   - See teacher load balance
   - Export timetable to CSV
   - Share with collaborators

### 💾 Database Models

- **User** - Plan creators
- **Plan** - Timetable plans with school/staff data
- **Collaboration** - Real-time team editing (WebSocket ready)
- **PlanHistory** - Audit trail for changes

### 🔄 Scheduling Algorithm

Greedy load-balancing approach:
1. Sort subjects by period requirement
2. For each period needed, find least-loaded day
3. Place subject in first available slot
4. Track teacher capacity; warn if exceeded
5. Validate all subjects have assigned teachers

### 🌐 API Endpoints

```
GET    /api/health                    # Health check
GET    /api/sample-data               # Sample data for demo
POST   /api/plans                     # Create plan
GET    /api/plans                     # List user's plans
GET    /api/plans/:id                 # Get specific plan
PUT    /api/plans/:id                 # Update plan
DELETE /api/plans/:id                 # Delete plan
POST   /api/plans/:id/generate        # Generate timetable
GET    /api/plans/:id/export/csv      # Export as CSV
GET    /api/plans/:id/collaborators   # List collaborators
POST   /api/plans/:id/collaborators   # Add collaborator
```

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/timetable_db

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# React
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_WS_URL=http://localhost:5000
```

## 🛠️ Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
flake8 .
black .

# Frontend linting
cd frontend
npm run lint
```

## 📦 Production Deployment

### Docker Production Build

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Setup

1. Update `.env` with production values
2. Enable HTTPS (use reverse proxy like Nginx)
3. Set up database backups
4. Configure monitoring & logging

## 🚢 Deployment Options

### AWS
- **Frontend**: S3 + CloudFront
- **Backend**: ECS/Fargate or EC2
- **Database**: RDS PostgreSQL

### Heroku
```bash
# Connect repo and deploy
git push heroku main
```

### DigitalOcean App Platform
- One-click deployment with Docker Compose support

### GCP Cloud Run
- Deploy containerized backend
- Static hosting for frontend

## 🤝 Real-Time Collaboration (WebSocket)

WebSocket events:
```javascript
// Connection
socket.on('connect', () => console.log('Connected'))

// Plan updates
socket.emit('plan_updated', { plan_id: 1, data: {...} })
socket.on('plan_changed', (data) => console.log('Plan changed:', data))

// Disconnection
socket.on('disconnect', () => console.log('Disconnected'))
```

## 📝 API Usage Examples

### Create a Plan
```bash
curl -X POST http://localhost:5000/api/plans \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Class 10 Timetable",
    "school_profile": {
      "institution_name": "High School",
      "days_per_week": 5,
      "periods_per_day": 6
    },
    "teachers": [...],
    "subjects": [...]
  }'
```

### Generate Timetable
```bash
curl -X POST http://localhost:5000/api/plans/1/generate
```

### Export as CSV
```bash
curl -X GET http://localhost:5000/api/plans/1/export/csv \
  -o timetable.csv
```

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres
```

### API Won't Start
```bash
# Check backend logs
docker-compose logs backend

# Verify .env DATABASE_URL
cat .env
```

### Frontend Can't Connect to API
```bash
# Check CORS_ORIGINS in .env
# Ensure backend is running: http://localhost:5000/api/health
```

## 📚 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Zustand |
| **Backend** | Flask, SQLAlchemy, Flask-CORS, Flask-SocketIO |
| **Database** | PostgreSQL 15 |
| **Deployment** | Docker, Docker Compose |
| **API** | REST + WebSocket (Socket.IO) |

## 📄 License

MIT License - Feel free to use for personal, educational, or commercial projects.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 💬 Support

- Check issue tracker for known problems
- Review API documentation in code comments
- Consult PostgreSQL/React documentation as needed

---

**Built with ❤️ | Happy Planning! 📅**
