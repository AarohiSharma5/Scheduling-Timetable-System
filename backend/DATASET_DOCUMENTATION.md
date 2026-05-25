# 📊 Realistic School Dataset Implementation

## Overview
Complete realistic school dataset with:
- **~2,800 Students** (Pre-Primary to Class 12)
- **75 Teachers** (NTT, PRT, TGT, PGT, Specialists)
- **1 Principal** + **5 Coordinators**
- **4 Houses** + **14 Classrooms**
- **20+ Subjects** with complete master data
- Proper age distribution, sections, academics

---

## 📈 Dataset Statistics

### Student Distribution (~2,800 total)

| Grade | Sections | Count | Notes |
|-------|----------|-------|-------|
| **Pre-Primary** | | | |
| Nursery | A,B,C | 78 | Ages 3-4 |
| LKG | A,B,C | 84 | Ages 4-5 |
| UKG | A,B,C | 81 | Ages 5-6 |
| **Primary** | | | |
| Class 1-5 | A,B,C,D each | 618 | Ages 6-11 |
| **Middle** | | | |
| Class 6-8 | A,B,C,D each | 422 | Ages 11-14 |
| **Secondary** | | | |
| Class 9-10 | A,B,C,D,E each | 456 | Ages 14-16 |
| **Senior Secondary** | | | |
| Class 11 Science | A,B | 260 | Age 16-17 |
| Class 11 Commerce | A | 130 | Age 16-17 |
| Class 11 Humanities | A | 130 | Age 16-17 |
| Class 12 Science | A,B | 270 | Age 17-18 |
| Class 12 Commerce | A | 135 | Age 17-18 |
| Class 12 Humanities | A | 136 | Age 17-18 |
| **TOTAL** | **73 sections** | **~2,800** | Realistic distribution |

### Teacher Distribution (75 total)

| Type | Count | Subjects |
|------|-------|----------|
| **NTT** (Pre-Primary) | 6 | Pre-Primary Activities |
| **PRT** (Primary) | 18 | English, Hindi, Math, EVS, Computer, GK, Art, Music |
| **TGT** (Middle/Secondary) | 28 | Hindi, English, Math, Science, Physics, Chemistry, Biology, SST, Sanskrit, Computer, PE, Art |
| **PGT** (Senior Secondary) | 18 | Physics, Chemistry, Biology, Math, Economics, Business, Accountancy, Political Science, History, Geography, English, CS |
| **Specialists** | 5 | Librarian, PTI, Dance, Music, Art |
| **TOTAL** | **75** | |

### Other Resources

| Resource | Count |
|----------|-------|
| Houses | 4 (Red, Blue, Green, Yellow) |
| Classrooms | 14 (including labs, library, auditorium) |
| Subject Masters | 20 |
| Coordinators | 5 |
| Principal | 1 |

---

## 🗄️ New Database Models

### 1. Student Model
```python
class Student(db.Model):
    student_id          # STU0001
    admission_no        # ADM240001
    user_id             # Link to auth User
    first_name          # Aarav
    last_name           # Sharma
    gender              # Male, Female
    date_of_birth       # 2012-07-14
    class_grade         # "1", "7", "11 Science", etc.
    section             # A, B, C, D
    roll_no             # 1-45 in each class
    house_id            # Which house (Red/Blue/Green/Yellow)
    father_name
    mother_name
    contact_number      # 98xxxxxxxx
    address             # City name
    transport_mode      # Bus, Private, Walk
    blood_group         # A+, B-, etc.
    admission_date
    status              # Active, Inactive, Left
```

### 2. House Model
```python
class House(db.Model):
    name                # "Red", "Blue", "Green", "Yellow"
    color               # HEX color code
    house_master_id     # Teacher assigned as house master
```

### 3. Classroom Model
```python
class Classroom(db.Model):
    room_id             # R101, R201, L101
    room_name           # "Nursery A", "Physics Lab"
    capacity            # 28-500
    room_type           # Classroom, Lab, Library, Hall, Activity
    assigned_class      # "5A" (if permanently assigned)
    facilities          # ["Smart Board", "AC", "Projector"]
    floor               # Ground, 1st, 2nd
```

### 4. SubjectMaster Model
```python
class SubjectMaster(db.Model):
    subject_id          # SUB01
    subject_name        # "English"
    subject_code        # "ENG"
    subject_type        # Core, Language, Practical, Activity
    min_periods_per_week
    max_periods_per_week
    applicable_classes  # ["1", "2", ... "12 Science", ...]
```

### 5. Principal Model
```python
class Principal(db.Model):
    principal_id        # P001
    user_id             # Link to auth User
    name                # Dr. Meera Kapoor
    qualification       # PhD Education
    experience_years    # 22
    email
    joining_date
    phone
```

### 6. Coordinator Model
```python
class Coordinator(db.Model):
    coordinator_id      # C001
    user_id             # Link to auth User
    name                # Anjali Sharma
    designation         # Pre Primary Coordinator
    responsibility      # "Nursery-UKG", "Classes 9-10"
    email
    phone
```

---

## ⚙️ How to Use

### Option 1: Load Realistic Dataset (NEW)

```bash
cd backend

# Load ~2,800 students + 75 teachers + all resources
python seed_realistic.py
```

**Output**:
```
❌ Dropping all tables...
📊 Creating all tables...
⚙️  Setting up school configuration...
   ✅ School config created

🏠 Creating houses...
   ✅ Created 4 houses

📚 Creating subject master data...
   ✅ Created 20 subject masters

📋 Creating batches (classes & sections)...
   ✅ Created 73 batches

🏢 Creating classrooms...
   ✅ Created 14 classrooms

👔 Creating principal...
   ✅ Principal created

📝 Creating coordinators...
   ✅ Created 5 coordinators

👨‍🏫 Creating 75 teachers with specializations...
   ✅ Created 75 teachers

👨‍🎓 Creating ~2,800 students...
   [500] students created...
   [1000] students created...
   ... etc ...
   ✅ Created 2800 students

📊 DATABASE STATISTICS:
   • Students: 2800
   • Teachers: 75
   • Coordinators: 5
   • Principals: 1
   • Batches/Sections: 73
   • Houses: 4
   • Classrooms: 14
   • Subject Masters: 20
   • Total Users: 2881
```

### Option 2: Load Original Sample Dataset

```bash
python seed.py
# Creates only 8 teachers, 6 classes (simple sample)
```

---

## 📊 Example Data

### Student Record
```json
{
  "student_id": "STU0345",
  "admission_no": "ADM240345",
  "first_name": "Aarav",
  "last_name": "Sharma",
  "gender": "Male",
  "date_of_birth": "2012-07-14",
  "class_grade": "7",
  "section": "B",
  "roll_no": 18,
  "house_id": 2,
  "house_name": "Blue",
  "father_name": "Mr. Rajesh Sharma",
  "mother_name": "Mrs. Priya Sharma",
  "contact_number": "9876543210",
  "address": "New Delhi",
  "transport_mode": "Bus",
  "blood_group": "B+",
  "admission_date": "2023-04-01",
  "status": "Active"
}
```

### Teacher Record
```json
{
  "teacher_id": "T034",
  "name": "Rajeev Kumar",
  "designation": "TGT",
  "subject": "Hindi",
  "subjects": [7],
  "assigned_batches": [23, 24],
  "is_class_teacher": true,
  "class_teacher_of": "7A",
  "experience_years": 11,
  "email": "rajeev.kumar@school.edu",
  "phone": "9876543210",
  "qualification": "M.A Hindi B.Ed",
  "has_duties": true,
  "max_periods_per_week": 28
}
```

### Coordinator Record
```json
{
  "coordinator_id": "C003",
  "name": "Ajay Mehta",
  "designation": "Middle School Coordinator",
  "responsibility": "Classes 6-8",
  "email": "ajay@school.edu",
  "phone": "98xxxxxxxx"
}
```

---

## 🔍 Query Examples

### Get all students in a class
```python
students = Student.query.filter_by(class_grade="7", section="B").all()
print(f"Total students in 7B: {len(students)}")
```

### Get all teachers of a subject
```python
math_teachers = Teacher.query.filter(
    Teacher.subject_ids.contains(3)  # Assume Math is ID 3
).all()
```

### Get students in a house
```python
blue_house_students = Student.query.filter_by(house_id=2).all()
```

### Get class teachers
```python
class_teachers = Teacher.query.filter_by(is_class_teacher=True).all()
```

### Get available classrooms
```python
available_labs = Classroom.query.filter_by(room_type="Lab").all()
```

---

## 🔗 Model Relationships

```
User (Parent)
├── Student
├── Teacher
├── Principal
└── Coordinator

Batch
├── Student (via class_grade + section)
└── Teacher (via assigned_batch_ids)

House
└── Student (via house_id)
└── Teacher (as house_master_id)

SubjectMaster
└── Teacher (via subject_ids)
└── Applicable to Batches

Classroom
└── Assigned to Batch (via assigned_class)

TimetableSlot
├── Batch
├── Teacher
└── Classroom (future)
```

---

## 📱 API Endpoints for Student/Teacher Data

```bash
# Get all students
GET /api/students?class=7&section=B

# Get student details
GET /api/students/{student_id}

# Get all teachers
GET /api/teachers

# Get teacher details
GET /api/teachers/{teacher_id}

# Get students in a house
GET /api/houses/{house_id}/students

# Get available classrooms
GET /api/classrooms?type=Lab

# Get coordinators
GET /api/coordinators

# Get principal
GET /api/principal
```

---

## 🧪 Test Queries

### 1. Check data distribution
```sql
SELECT class_grade, section, COUNT(*) as count 
FROM students 
GROUP BY class_grade, section 
ORDER BY class_grade, section;
```

### 2. Find teachers without assigned classes  
```sql
SELECT name FROM teachers 
WHERE JSON_LENGTH(assigned_batch_ids) = 0;
```

### 3. Check student-teacher ratio per class
```sql
SELECT 
  s.class_grade, s.section,
  COUNT(s.id) as student_count,
  COUNT(DISTINCT t.id) as teacher_count
FROM students s
LEFT JOIN teachers t ON t.id IN (SELECT id FROM teachers WHERE assigned_batch_ids LIKE CONCAT('%"', ...))
GROUP BY s.class_grade, s.section;
```

### 4. Get house distribution
```sql
SELECT h.name, COUNT(s.id) as student_count
FROM houses h
LEFT JOIN students s ON s.house_id = h.id
GROUP BY h.name;
```

---

## 📋 Database Size

With ~2,800 students + 75 teachers:

| Table | Rows | Est. Size |
|-------|------|-----------|
| students | 2,800 | ~850 KB |
| teachers | 75 | ~25 KB |
| batches | 73 | ~20 KB |
| users | 2,881 | ~300 KB |
| subject_masters | 20 | ~10 KB |
| classrooms | 14 | ~5 KB |
| coordinators | 5 | ~2 KB |
| **TOTAL** | **~6,000** | **~1.2 MB** |

SQLite handles this easily. For production, migrate to PostgreSQL.

---

## 🚀 Next Steps

### 1. Load Data
```bash
python seed_realistic.py
python -m flask run --port=5000
```

### 2. Test Endpoints
```bash
# Get all students in class 7B
curl http://localhost:5000/api/students?class=7&section=B \
  -H "Authorization: Bearer {token}"

# Get teacher info
curl http://localhost:5000/api/teachers/1 \
  -H "Authorization: Bearer {token}"
```

### 3. Frontend Integration
- Render student lists
- Show class-wise dashboards
- Display teacher profiles
- Visualize house competitions

### 4. Add APIs (To be created)
```
GET  /api/students
GET  /api/students/{id}
POST /api/students
PUT  /api/students/{id}
GET  /api/students/class/{grade}/{section}
GET  /api/teachers
GET  /api/teachers/{id}
GET  /api/coordinators
GET  /api/principal
GET  /api/houses
GET  /api/classrooms
```

---

## 📊 Data Size Comparison

### Original seed.py
- 8 Teachers
- 6 Classes
- ~300 Students
- Total Users: 315

### New seed_realistic.py
- 75 Teachers
- 73 Classes
- ~2,800 Students  
- 5 Coordinators
- 1 Principal
- **Total Users: 2,881 (9x larger)**

Perfect for testing:
✅ Large-scale timetable generation  
✅ Student/teacher performance analytics  
✅ House competition tracking  
✅ Classroom resource allocation  
✅ Staff workload analysis  
✅ Multi-section subject handling

---

## ✅ Verification

After seeding:

```bash
# Check total students
sqlite3 timetable.db "SELECT COUNT(*) FROM students;"
# Output: 2800

# Check total teachers
sqlite3 timetable.db "SELECT COUNT(*) FROM teachers;"
# Output: 75

# Check class distribution
sqlite3 timetable.db "SELECT class_grade, COUNT(*) FROM students GROUP BY class_grade;"
```

---

## 🔐 Security

All test password hashes generated with `werkzeug.security.generate_password_hash`

- Principal: principal@school.edu / principal123
- Coordinator: anjali@school.edu / coordinator123
- Teacher: priya.sharma@school.edu / teacher123
- Admin: admin@school.edu / admin123

Change immediately in production!

---

## 📚 Related Files

- **Models**: [backend/models.py](models.py) - All 6 new models
- **Seed Script**: [backend/seed_realistic.py](seed_realistic.py) - Data generation
- **Original Seed**: [backend/seed.py](seed.py) - Simple sample seed

---

**Dataset Status**: ✅ Complete & Ready  
**Last Updated**: 25 May 2026  
**Total Records**: ~2,881 users + 2,800 students + 75 teachers
