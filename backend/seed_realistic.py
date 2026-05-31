"""
Comprehensive Database Seed Script with Realistic School Dataset
~2,800 students | 75 teachers | Principal | Coordinators | Classrooms | Houses
"""

import os
import sys
sys.path.insert(0, '.')

from app import create_app
from models import (
    db, User, Batch, Subject, Teacher, SchoolConfig, Timetable, TimetableSlot,
    LeaveRequest, Notification, Student, Classroom, House, Principal, Coordinator,
    SubjectMaster, Organization, PinnedSlot, Charge
)
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
import random
import string


# ---------------------------------------------------------------------------
# Default organization for the seeded dataset.
# Used by the "Login as Organisation" flow on the frontend.
# ---------------------------------------------------------------------------
DEFAULT_ORG_NAME = "Test Sample Institute"
DEFAULT_ORG_SLUG = "test-sample-institute"
DEFAULT_ORG_PASSWORD = "institute123"

# Data generation helpers
FIRST_NAMES_MALE = [
    "Aarav", "Aditya", "Arjun", "Amit", "Anuj", "Akash", "Ashwin",
    "Rohan", "Rahul", "Rishabh", "Rajeev", "Rajesh",
    "Vikram", "Vivek", "Varun", "Vicky",
    "Nikhil", "Naman", "Naveen",
    "Prateek", "Pawan", "Parth", "Puneet",
    "Sanjay", "Sandeep", "Sameer", "Samir", "Sushant", "Sunil",
    "Karan", "Kabir", "Kunal",
    "Anand", "Aman", "Ajay", "Arpit", "Akshay"
]

FIRST_NAMES_FEMALE = [
    "Aadhya", "Aisha", "Anjali", "Ananya", "Amita", "Avni", "Asha",
    "Diya", "Darshana", "Divya",
    "Esha", "Eun", "Eva",
    "Fatima", "Farida", "Freya",
    "Geeta", "Gitika", "Geetha",
    "Hema", "Hira", "Harsha",
    "Isha", "Irina", "Ishita",
    "Jaya", "Jyoti", "Jessica",
    "Kavya", "Kalpana", "Kanika", "Kaur",
    "Lavanya", "Lakshmi", "Leela", "Liza",
    "Megha", "Meera", "Meisha", "Mona",
    "Neha", "Nikita", "Nisha", "Natasha",
    "Olivia", "Oprah",
    "Pooja", "Priya", "Preeti", "Pallavi",
    "Ria", "Rutvi", "Riya",
    "Sneha", "Siya", "Simran", "Sunita", "Sonal",
    "Tanya", "Tara",
    "Usha", "Uma",
    "Veda", "Veena", "Vedica",
    "Wanda", "Winny",
    "Ximena", "Xanthe",
    "Yara", "Yasmin",
    "Zara", "Zainab"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Mehta",
    "Reddy", "Rao", "Nair", "Desai", "Malhotra", "Chopra", "Khanna",
    "Kapoor", "Bhatnagar", "Saxena", "Mishra", "Pandey", "Agarwal",
    "Dubey", "Tiwari", "Srivastava", "Tripathi", "Dwivedi",
    "Das", "Dutta", "Banerjee", "Mukherjee", "Chatterjee",
    "Joshi", "Roy", "Bhattacharya", "Iyengar", "Subramaniam",
    "Hegde", "Pillai", "Bhat", "Basak", "Bhola"
]

SUBJECTS_DATA = [
    # Pre-primary (Nursery / LKG / UKG) — activity-led, short day.
    ("SUB21", "Rhymes & Poems", "RHY", "PrePrimary", ["Nursery", "LKG", "UKG"]),
    ("SUB22", "Story Time", "STO", "PrePrimary", ["Nursery", "LKG", "UKG"]),
    ("SUB23", "Numbers & Counting", "NUM", "PrePrimary", ["Nursery", "LKG", "UKG"]),
    ("SUB24", "Alphabets & Phonics", "ALP", "PrePrimary", ["Nursery", "LKG", "UKG"]),
    ("SUB25", "Drawing & Play", "DRW", "PrePrimary", ["Nursery", "LKG", "UKG"]),
    ("SUB01", "English", "ENG", "Core", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11 Science", "11 Commerce", "11 Humanities", "12 Science", "12 Commerce", "12 Humanities"]),
    ("SUB02", "Hindi", "HIN", "Core", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]),
    ("SUB03", "Mathematics", "MTH", "Core", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11 Science", "11 Commerce", "12 Science", "12 Commerce"]),
    ("SUB04", "Science", "SCI", "Core", ["1", "2", "3", "4", "5", "6", "7", "8"]),
    ("SUB05", "Physics", "PHY", "Core", ["9", "10", "11 Science", "12 Science"]),
    ("SUB06", "Chemistry", "CHE", "Core", ["9", "10", "11 Science", "12 Science"]),
    ("SUB07", "Biology", "BIO", "Core", ["9", "10", "11 Science", "12 Science"]),
    ("SUB08", "Social Science", "SST", "Core", ["6", "7", "8", "9", "10"]),
    ("SUB09", "History", "HIS", "Core", ["9", "10", "11 Humanities", "12 Humanities"]),
    ("SUB10", "Geography", "GEO", "Core", ["9", "10", "11 Humanities", "12 Humanities"]),
    ("SUB11", "Political Science", "POL", "Core", ["11 Humanities", "12 Humanities"]),
    ("SUB12", "Economics", "ECO", "Core", ["11 Commerce", "11 Humanities", "12 Commerce", "12 Humanities"]),
    ("SUB13", "Accountancy", "ACC", "Core", ["11 Commerce", "12 Commerce"]),
    ("SUB14", "Business Studies", "BST", "Core", ["11 Commerce", "12 Commerce"]),
    ("SUB15", "Sanskrit", "SAN", "Language", ["6", "7", "8", "9", "10"]),
    ("SUB16", "Computer Science", "CSE", "Practical", ["6", "7", "8", "9", "10", "11 Science", "11 Commerce", "12 Science", "12 Commerce"]),
    ("SUB17", "Physical Education", "PE", "Activity", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11 Science", "11 Commerce", "11 Humanities", "12 Science", "12 Commerce", "12 Humanities"]),
    ("SUB18", "Art", "ART", "Activity", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]),
    ("SUB19", "Music", "MUS", "Activity", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]),
    ("SUB20", "GK", "GK", "Activity", ["1", "2", "3", "4", "5"]),
]

CLASS_DISTRIBUTION = {
    "Nursery": {"sections": ["A", "B", "C"], "count": 78},
    "LKG": {"sections": ["A", "B", "C"], "count": 84},
    "UKG": {"sections": ["A", "B", "C"], "count": 81},
    "1": {"sections": ["A", "B", "C", "D"], "count": 124},
    "2": {"sections": ["A", "B", "C", "D"], "count": 118},
    "3": {"sections": ["A", "B", "C", "D"], "count": 126},
    "4": {"sections": ["A", "B", "C", "D"], "count": 122},
    "5": {"sections": ["A", "B", "C", "D"], "count": 128},
    "6": {"sections": ["A", "B", "C", "D"], "count": 144},
    "7": {"sections": ["A", "B", "C", "D"], "count": 141},
    "8": {"sections": ["A", "B", "C", "D"], "count": 137},
    "9": {"sections": ["A", "B", "C", "D", "E"], "count": 225},
    "10": {"sections": ["A", "B", "C", "D", "E"], "count": 231},
    "11 Science": {"sections": ["A", "B"], "count": 260},
    "11 Commerce": {"sections": ["A"], "count": 130},
    "11 Humanities": {"sections": ["A"], "count": 130},
    "12 Science": {"sections": ["A", "B"], "count": 270},
    "12 Commerce": {"sections": ["A"], "count": 135},
    "12 Humanities": {"sections": ["A"], "count": 136},
}

HOUSES = [
    {"name": "Red", "color": "#FF0000"},
    {"name": "Blue", "color": "#0000FF"},
    {"name": "Green", "color": "#00AA00"},
    {"name": "Yellow", "color": "#FFFF00"},
]

CLASSROOMS_DATA = [
    ("R101", "Nursery A", 28, "Classroom", "Nursery A", ["Smart Board", "AC"], 1),
    ("R102", "Nursery B", 28, "Classroom", "Nursery B", [], 1),
    ("R103", "Nursery C", 28, "Classroom", "Nursery C", [], 1),
    ("R104", "Class 1A", 38, "Classroom", "1 A", ["Projector", "AC"], 1),
    ("R105", "Class 5A", 38, "Classroom", "5 A", ["Smart Board"], 1),
    ("R106", "Class 9A", 44, "Classroom", "9 A", ["Smart Board", "AC"], 2),
    ("R201", "Physics Lab", 45, "Lab", None, ["Bunsen Burner", "Microscope", "Apparatus"], 2),
    ("R202", "Chemistry Lab", 40, "Lab", None, ["Fume Hood", "Balance", "Chemicals"], 2),
    ("R203", "Biology Lab", 40, "Lab", None, ["Microscope", "Models", "Specimens"], 2),
    ("R204", "Computer Lab 1", 45, "Lab", None, ["Computers", "Projector", "AC"], 2),
    ("R301", "Library", 120, "Library", None, ["Books", "Digital Resources", "Reading Tables"], 1),
    ("R401", "Music Room", 35, "Activity", None, ["Instruments", "Sound System"], 1),
    ("R402", "Art Room", 35, "Activity", None, ["Art Supplies", "Tables"], 1),
    ("R501", "Auditorium", 500, "Hall", None, ["Sound System", "Lights", "Stage"], 0),
]


def seed_database():
    """Comprehensive database seeding with ~2,800 students and 75 teachers"""
    
    app = create_app()
    with app.app_context():
        # Drop and recreate all tables
        print("⚠️  Dropping all tables...")
        db.drop_all()
        
        print("📊 Creating all tables...")
        db.create_all()

        # =====================================================================
        # 0. ORGANIZATION (tenant)
        # =====================================================================
        print(f"\n🏫 Creating organization: {DEFAULT_ORG_NAME}...")
        organization = Organization(
            name=DEFAULT_ORG_NAME,
            slug=DEFAULT_ORG_SLUG,
            password_hash=generate_password_hash(DEFAULT_ORG_PASSWORD),
            description="Demo institute pre-loaded with 2,800 students, 75 teachers, and a full timetable.",
            logo_url="/scheduler-logo.png",
        )
        db.session.add(organization)
        db.session.commit()
        org_id = organization.id
        print(f"   ✅ Organization created (id={org_id}, slug={DEFAULT_ORG_SLUG}, password={DEFAULT_ORG_PASSWORD})")

        # =====================================================================
        # 1. SCHOOL CONFIGURATION
        # =====================================================================
        print("⚙️  Setting up school configuration...")
        # 08:00–14:00 with 45-min periods = 8 period slots; period 5 (11:00–11:45)
        # is lunch. periods_per_day is derived from the hours and kept here only
        # as a cached value (the engine/PDF recompute it from the window).
        school_config = SchoolConfig(
            id=1,
            organization_id=org_id,
            start_time="08:00",
            end_time="14:00",
            lunch_start="11:00",
            lunch_end="11:45",
            period_duration=45,
            periods_per_day=8,
            has_lunch_break=True,
            working_days=5,
            target_contact_periods_per_week=40,
            class_teacher_hours_per_week=5,
        )
        db.session.add(school_config)
        db.session.commit()
        print("   ✅ School config created")
        # NOTE: The charge catalog (club/house/exam duties, etc.), their weekly
        # hours, and the class-teacher time are intentionally NOT seeded — they
        # are real-world policy the coordinator enters in the Charges tab and
        # Configuration → Teacher Workload. The system never assumes them.
        
        # =====================================================================
        # 2. HOUSES
        # =====================================================================
        print("\n🏠 Creating houses...")
        houses = []
        for house_data in HOUSES:
            house = House(name=house_data["name"], color=house_data["color"])
            db.session.add(house)
            houses.append(house)
        db.session.commit()
        print(f"   ✅ Created {len(houses)} houses")
        
        # =====================================================================
        # 3. SUBJECT MASTERS
        # =====================================================================
        print("\n📚 Creating subject master data...")
        subject_masters = []
        for subject_id, name, code, subject_type, applicable_classes in SUBJECTS_DATA:
            subj = SubjectMaster(
                subject_id=subject_id,
                subject_name=name,
                subject_code=code,
                subject_type=subject_type,
                applicable_classes=applicable_classes,
                min_periods_per_week=4 if subject_type == "Core" else 2,
                max_periods_per_week=8 if subject_type == "Core" else 4,
            )
            db.session.add(subj)
            subject_masters.append(subj)
        db.session.commit()
        print(f"   ✅ Created {len(subject_masters)} subject masters")
        
        # =====================================================================
        # 4. BATCHES (CLASSES/SECTIONS)
        # =====================================================================
        print("\n📋 Creating batches (classes & sections)...")

        def grade_day_length(grade):
            """Younger grades have shorter days (fewer periods)."""
            if grade in ("Nursery", "LKG", "UKG"):
                return 4   # ends ~11:00, before lunch
            if grade in ("1", "2", "3", "4", "5"):
                return 6   # ends ~12:30
            return 8       # full day to 14:00 for middle/secondary/senior

        batches = []
        for grade, grade_data in CLASS_DISTRIBUTION.items():
            for section in grade_data["sections"]:
                batch = Batch(
                    organization_id=org_id,
                    grade=grade,
                    section=section,
                    student_count=grade_data["count"] // len(grade_data["sections"]),
                    periods_per_day=grade_day_length(grade),
                )
                db.session.add(batch)
                batches.append(batch)
        db.session.commit()
        print(f"   ✅ Created {len(batches)} batches")

        # =====================================================================
        # 4b. SUBJECTS + BATCH WIRING (consumed by the scheduling engine)
        # The engine reads the simple `Subject` table and `batch.subject_ids`,
        # so we must materialise them from SUBJECTS_DATA here.
        # =====================================================================
        print("\n📗 Creating subjects and linking them to batches...")
        grade_to_batches = {}
        for b in batches:
            grade_to_batches.setdefault(b.grade, []).append(b)

        # Lab subjects run as consecutive double periods (one block/day); every
        # subject is also capped at one period/day per class (spacing) unless
        # it's a lab, which needs two consecutive periods.
        LAB_SUBJECTS = {"Computer Science", "Physics", "Chemistry", "Biology"}

        # Weekly periods per subject type. Pre-primary subjects get 4 each so the
        # 5 pre-primary subjects fill a short 4-period × 5-day junior week.
        PERIODS_BY_TYPE = {"Core": 5, "Language": 4, "Practical": 4, "PrePrimary": 4, "Activity": 2}

        subjects = []
        subject_by_name = {}
        for _sid, name, _code, subject_type, applicable_classes in SUBJECTS_DATA:
            periods = PERIODS_BY_TYPE.get(subject_type, 3)
            applicable_batches = []
            for grade in applicable_classes:
                applicable_batches.extend(grade_to_batches.get(grade, []))
            is_lab = name in LAB_SUBJECTS
            subject = Subject(
                organization_id=org_id,
                name=name,
                periods_per_week=periods,
                max_periods_per_day=2 if is_lab else 1,
                requires_double=is_lab,
                batch_ids=[b.id for b in applicable_batches],
            )
            db.session.add(subject)
            subjects.append(subject)
            subject_by_name[name] = subject
        db.session.commit()

        # Tell each batch which subjects it takes.
        for b in batches:
            b.subject_ids = [s.id for s in subjects if b.id in (s.batch_ids or [])]
        db.session.commit()
        print(f"   ✅ Created {len(subjects)} subjects and linked them to batches")

        # =====================================================================
        # 5. CLASSROOMS
        # =====================================================================
        print("\n🏢 Creating classrooms...")
        classrooms = []
        for room_id, room_name, capacity, room_type, assigned_class, facilities, floor in CLASSROOMS_DATA:
            classroom = Classroom(
                room_id=room_id,
                room_name=room_name,
                capacity=capacity,
                room_type=room_type,
                assigned_class=assigned_class,
                facilities=facilities,
                floor=floor
            )
            db.session.add(classroom)
            classrooms.append(classroom)
        db.session.commit()
        print(f"   ✅ Created {len(classrooms)} classrooms")
        
        # =====================================================================
        # 6. PRINCIPALS
        # =====================================================================
        # Admin user (needed for managing the system)
        print("\n🛠️  Creating admin user...")
        admin_user = User(
            organization_id=org_id,
            name="School Admin",
            email="admin@school.edu",
            role="admin",
            password_hash=generate_password_hash("admin123"),
        )
        db.session.add(admin_user)
        db.session.commit()
        print("   ✅ Admin user created (admin@school.edu / admin123)")

        print("\n👔 Creating principal...")
        principal_user = User(
            organization_id=org_id,
            name="Dr. Meera Kapoor",
            email="principal@school.edu",
            role="principal",
            password_hash=generate_password_hash("principal123"),
        )
        db.session.add(principal_user)
        db.session.commit()
        
        principal = Principal(
            principal_id="P001",
            user_id=principal_user.id,
            name="Dr. Meera Kapoor",
            qualification="PhD Education",
            experience_years=22,
            email="principal@school.edu",
            joining_date=date(2014, 4, 1),
            phone="9876543210"
        )
        db.session.add(principal)
        db.session.commit()
        print("   ✅ Principal created")
        
        # =====================================================================
        # 7. COORDINATORS
        # =====================================================================
        print("\n📝 Creating coordinators...")
        coordinators_data = [
            ("C001", "Anjali Sharma", "Pre Primary Coordinator", "Nursery-UKG", "anjali@school.edu"),
            ("C002", "Ritika Verma", "Junior Coordinator", "Classes 1-5", "ritika@school.edu"),
            ("C003", "Ajay Mehta", "Middle School Coordinator", "Classes 6-8", "ajay@school.edu"),
            ("C004", "Sonal Gupta", "Secondary Coordinator", "Classes 9-10", "sonal@school.edu"),
            ("C005", "Vivek Sharma", "Senior Secondary Coordinator", "Classes 11-12", "vivek@school.edu"),
        ]
        
        coordinators = []
        for coord_id, name, designation, responsibility, email in coordinators_data:
            coord_user = User(
                organization_id=org_id,
                name=name,
                email=email,
                role="coordinator",
                password_hash=generate_password_hash("coordinator123"),
            )
            db.session.add(coord_user)
            db.session.commit()
            
            coordinator = Coordinator(
                coordinator_id=coord_id,
                user_id=coord_user.id,
                name=name,
                designation=designation,
                responsibility=responsibility,
                email=email,
                phone="98" + "".join([str(random.randint(0, 9)) for _ in range(8)])
            )
            db.session.add(coordinator)
            coordinators.append(coordinator)
        db.session.commit()
        print(f"   ✅ Created {len(coordinators)} coordinators")
        
        # =====================================================================
        # 8. TEACHERS (75 TOTAL)
        # =====================================================================
        print("\n👨‍🏫 Creating 75 teachers with specializations...")
        
        teacher_data_list = [
            # NTT Teachers (6)
            ("Priya Sharma", "priya.sharma@school.edu", "NTT", "Pre-Primary Activities", ["Nursery A"]),
            ("Neha Verma", "neha.verma@school.edu", "NTT", "Pre-Primary Activities", ["Nursery B"]),
            ("Pooja Gupta", "pooja.gupta@school.edu", "NTT", "Pre-Primary Activities", ["Nursery C"]),
            ("Sunita Singh", "sunita.singh@school.edu", "NTT", "Pre-Primary Activities", ["LKG A", "LKG B"]),
            ("Anjali Patel", "anjali.patel@school.edu", "NTT", "Pre-Primary Activities", ["UKG A", "UKG B"]),
            ("Deepa Kapoor", "deepa.kapoor@school.edu", "NTT", "Pre-Primary Activities", ["UKG C"]),
        ]
        
        # Add PRT teachers (18)
        prt_subjects = ["English", "Hindi", "Mathematics", "EVS", "Computer", "GK", "Art", "Music"]
        for i in range(18):
            subject = prt_subjects[i % len(prt_subjects)]
            class_range = str((i % 5) + 1)  # Classes 1-5
            section = ["A", "B", "C", "D"][i % 4]
            teacher_data_list.append((
                f"{random.choice(FIRST_NAMES_MALE if random.choice([True, False]) else FIRST_NAMES_FEMALE)} {random.choice(LAST_NAMES)}",
                f"t{i+1}@school.edu",
                "PRT",
                subject,
                [f"{class_range} {section}"]
            ))
        
        # Add TGT teachers (28)
        tgt_subjects = ["Hindi", "English", "Mathematics", "Science", "Physics", "Chemistry", "Biology", "Social Science", "Sanskrit", "Computer", "PE", "Art"]
        for i in range(28):
            subject = tgt_subjects[i % len(tgt_subjects)]
            class_range = str((6 + (i % 3)))  # Classes 6-8
            section = ["A", "B", "C", "D"][i % 4]
            teacher_data_list.append((
                f"{random.choice(FIRST_NAMES_MALE if random.choice([True, False]) else FIRST_NAMES_FEMALE)} {random.choice(LAST_NAMES)}",
                f"t{i+19}@school.edu",
                "TGT",
                subject,
                [f"{class_range} {section}"]
            ))
        
        # Add PGT teachers (18)
        pgt_subjects = ["Physics", "Chemistry", "Biology", "Mathematics", "Economics", "Business Studies", "Accountancy", "Political Science", "History", "Geography", "English", "Computer Science"]
        for i in range(18):
            subject = pgt_subjects[i % len(pgt_subjects)]
            stream = ["11 Science", "11 Commerce", "11 Humanities", "12 Science", "12 Commerce", "12 Humanities"][i % 6]
            teacher_data_list.append((
                f"{random.choice(FIRST_NAMES_MALE if random.choice([True, False]) else FIRST_NAMES_FEMALE)} {random.choice(LAST_NAMES)}",
                f"t{i+47}@school.edu",
                "PGT",
                subject,
                [stream]
            ))
        
        # Add specialist teachers (5)
        specialists = [
            ("Rajesh Kumar", "rajesh.librarian@school.edu", "Specialist", "Librarian", []),
            ("Vikram Singh", "vikram.pti@school.edu", "Specialist", "PTI", []),
            ("Maya Devi", "maya.dance@school.edu", "Specialist", "Dance", []),
            ("Kavya Sharma", "kavya.music@school.edu", "Specialist", "Music", []),
            ("Arjun Verma", "arjun.art@school.edu", "Specialist", "Art", []),
        ]
        teacher_data_list.extend(specialists)
        
        # Create teacher users and teacher profiles
        teachers = []
        teacher_count = 0
        for name, email, designation, subject, assigned_batches in teacher_data_list[:75]:  # Limit to 75
            teacher_user = User(
                organization_id=org_id,
                name=name,
                email=email,
                role="teacher",
                password_hash=generate_password_hash("teacher123"),
            )
            db.session.add(teacher_user)
            db.session.commit()
            
            # Map the teacher's declared subject onto the Subject table that the
            # scheduler actually reads (NTT/specialist subjects simply won't match).
            subject_ids = []
            matched_subject = subject_by_name.get(subject)
            if matched_subject:
                subject_ids.append(matched_subject.id)
            
            # Get batch IDs for assigned batches
            assigned_batch_ids = []
            for batch in batches:
                batch_display = f"{batch.grade} {batch.section}"
                if batch_display in assigned_batches:
                    assigned_batch_ids.append(batch.id)
            
            teacher = Teacher(
                organization_id=org_id,
                user_id=teacher_user.id,
                teacher_code=f"TCHR{str(teacher_count + 1).zfill(4)}",
                name=name,
                email=email,
                subject_ids=subject_ids,
                assigned_batch_ids=assigned_batch_ids,
                is_class_teacher=len(assigned_batches) > 0 and designation != "Specialist",
                class_teacher_batch_id=assigned_batch_ids[0] if assigned_batch_ids else None,
                has_duties=random.choice([True, False]),
                max_periods_per_week=32 if designation in ["NTT", "PRT"] else 28
            )
            db.session.add(teacher)
            teachers.append(teacher)
            teacher_count += 1
        
        db.session.commit()
        print(f"   ✅ Created {teacher_count} teachers")

        # =====================================================================
        # 8b. SCHEDULER COVERAGE
        # Guarantee every (batch, subject) the batch needs has at least one
        # eligible teacher: someone who teaches that subject AND is assigned to
        # that batch. Otherwise the engine has nothing valid to place.
        # =====================================================================
        print("\n🔗 Wiring teachers ↔ subjects ↔ batches for schedule coverage...")

        # Pool of teachers per subject id, based on what each teacher teaches.
        teachers_for_subject = {s.id: [] for s in subjects}
        for t in teachers:
            for sid in (t.subject_ids or []):
                if sid in teachers_for_subject:
                    teachers_for_subject[sid].append(t)

        # Size each subject's teacher pool to its real weekly demand so no single
        # teacher is asked to cover more sections than their weekly max allows.
        # demand = periods/week × number of sections taking the subject; with a
        # ~20-period working budget per teacher we need ceil(demand / 20) of them.
        import math
        batches_per_subject = {s.id: 0 for s in subjects}
        for b in batches:
            for sid in (b.subject_ids or []):
                if sid in batches_per_subject:
                    batches_per_subject[sid] += 1

        TEACHER_BUDGET = 20  # periods/week we plan per teacher (max is 24, leave slack)
        rr = 0
        for s in subjects:
            demand = (s.periods_per_week or 1) * batches_per_subject.get(s.id, 0)
            needed = max(1, math.ceil(demand / TEACHER_BUDGET))
            # Add teachers (round-robin across the whole staff) until the pool is
            # big enough; skip anyone already in this subject's pool.
            guard = 0
            while len(teachers_for_subject[s.id]) < needed and guard < len(teachers) * 2:
                t = teachers[rr % len(teachers)]
                rr += 1
                guard += 1
                if t not in teachers_for_subject[s.id]:
                    if s.id not in (t.subject_ids or []):
                        t.subject_ids = list(t.subject_ids or []) + [s.id]
                    teachers_for_subject[s.id].append(t)

        # For each batch+subject pair, make sure a teacher of that subject is
        # assigned to the batch (spread the load round-robin within each pool).
        assign_cursor = {s.id: 0 for s in subjects}
        for b in batches:
            for sid in (b.subject_ids or []):
                pool = teachers_for_subject.get(sid, [])
                if not pool:
                    continue
                if any(b.id in (t.assigned_batch_ids or []) for t in pool):
                    continue
                t = pool[assign_cursor[sid] % len(pool)]
                assign_cursor[sid] += 1
                t.assigned_batch_ids = list(t.assigned_batch_ids or []) + [b.id]
        db.session.commit()
        print("   ✅ Teacher / subject / batch coverage ensured")

        # =====================================================================
        # 8b. STRUCTURED ASSIGNMENTS + DYNAMIC CONTACT HOURS
        # Build per-subject batch lists (so "Maths → 9, 8" is explicit). Charges
        # and class-teacher hours are left empty/zero for the coordinator to set;
        # with no charges every teacher's capacity equals the target.
        # =====================================================================
        print("\n🧩 Building structured teaching assignments...")
        batch_by_id = {b.id: b for b in batches}
        TARGET = 40
        CT_HOURS = 5  # matches the org's class_teacher_hours_per_week above
        for t in teachers:
            assigned = list(t.assigned_batch_ids or [])
            assignments = []
            for sid in (t.subject_ids or []):
                # This subject is taught only to the teacher's batches that
                # actually take it.
                bids = [bid for bid in assigned
                        if batch_by_id.get(bid) and sid in (batch_by_id[bid].subject_ids or [])]
                if bids:
                    assignments.append({"subject_id": sid, "batch_ids": sorted(set(bids))})
            t.teaching_assignments = assignments
            t.charges = []  # extra charges left for the coordinator to add
            # Capacity = target minus reserved class-teacher hours (if a CT).
            t.max_periods_per_week = TARGET - (CT_HOURS if t.is_class_teacher else 0)
        db.session.commit()
        print("   ✅ Teaching assignments set; capacity = target − class-teacher hours "
              f"(target {TARGET}, CT {CT_HOURS})")

        # =====================================================================
        # 8c. CONSTRAINT DEMO: teacher availability + a pinned/fixed period
        # Showcases the scheduler honoring real-world constraints.
        # =====================================================================
        print("\n🚦 Seeding sample availability + a pinned period...")
        if teachers:
            # First teacher can't take the first two periods on Monday.
            teachers[0].unavailable_slots = [
                {"day": "Monday", "period": 1},
                {"day": "Monday", "period": 2},
            ]
            # Another teacher is off on Friday afternoon.
            if len(teachers) > 10:
                teachers[10].unavailable_slots = [
                    {"day": "Friday", "period": 5},
                    {"day": "Friday", "period": 6},
                ]
        db.session.commit()

        # Pin one class's first subject to Monday period 1 (e.g. a fixed slot).
        # Use the first batch that actually has subjects (early grades may not).
        pin_batch = next((b for b in batches if b.subject_ids), None)
        if pin_batch:
            db.session.add(PinnedSlot(
                organization_id=org_id,
                batch_id=pin_batch.id,
                subject_id=pin_batch.subject_ids[0],
                day="Monday",
                period_number=1,
            ))
            db.session.commit()
            print(f"   ✅ Availability + pinned period seeded (pinned batch {pin_batch.id})")
        else:
            print("   ✅ Availability seeded (no batch with subjects to pin)")

        # =====================================================================
        # 9. STUDENTS (~2,800 TOTAL)
        # =====================================================================
        print("\n👨‍🎓 Creating ~2,800 students...")
        student_count = 0
        admission_counter = 240001
        
        for class_grade, grade_data in CLASS_DISTRIBUTION.items():
            for section in grade_data["sections"]:
                students_in_section = grade_data["count"] // len(grade_data["sections"])
                
                for roll_no in range(1, students_in_section + 1):
                    is_male = random.choice([True, False])
                    first_name = random.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
                    last_name = random.choice(LAST_NAMES)
                    
                    # Generate dates  students would be appropriate age
                    if class_grade in ["Nursery", "LKG", "UKG"]:
                        dob = date(random.randint(2022, 2023), random.randint(1, 12), random.randint(1, 28))
                    elif class_grade in ["1", "2", "3", "4", "5"]:
                        dob = date(random.randint(2019, 2020), random.randint(1, 12), random.randint(1, 28))
                    elif class_grade in ["6", "7", "8"]:
                        dob = date(random.randint(2016, 2017), random.randint(1, 12), random.randint(1, 28))
                    elif class_grade in ["9", "10"]:
                        dob = date(random.randint(2014, 2015), random.randint(1, 12), random.randint(1, 28))
                    else:  # 11, 12
                        dob = date(random.randint(2007, 2008), random.randint(1, 12), random.randint(1, 28))
                    
                    student_id = f"STU{str(student_count + 1).zfill(4)}"
                    admission_no = f"ADM{admission_counter}"
                    admission_counter += 1
                    
                    student = Student(
                        organization_id=org_id,
                        student_id=student_id,
                        admission_no=admission_no,
                        first_name=first_name,
                        last_name=last_name,
                        gender="Male" if is_male else "Female",
                        date_of_birth=dob,
                        class_grade=class_grade,
                        section=section,
                        roll_no=roll_no,
                        house_id=random.choice(houses).id,
                        father_name=f"{random.choice(['Mr. '])}{random.choice(LAST_NAMES)}",
                        mother_name=f"{random.choice(['Mrs. '])}{random.choice(FIRST_NAMES_FEMALE)} {random.choice(LAST_NAMES)}",
                        contact_number="9" + "8" + "".join([str(random.randint(0, 9)) for _ in range(8)]),
                        address=random.choice(["New Delhi", "Noida", "Gurgaon", "Bangalore", "Mumbai", "Pune", "Chennai", "Hyderabad"]),
                        transport_mode=random.choice(["Bus", "Private", "Walk"]),
                        blood_group=random.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
                        admission_date=date(2023, 4, 1),
                        status=random.choice(["Active", "Active", "Active", "Inactive"])  # Most are active
                    )
                    db.session.add(student)
                    student_count += 1
                    
                    if student_count % 500 == 0:
                        print(f"   [{student_count}] students created...")
                    
                    if student_count % 100 == 0:
                        db.session.commit()
        
        db.session.commit()
        print(f"   ✅ Created {student_count} students")
        
        # =====================================================================
        # 10. SUMMARY
        # =====================================================================
        print("\n" + "=" * 70)
        print("✅ COMPREHENSIVE DATABASE SEEDING COMPLETE!")
        print("=" * 70)
        
        stats = {
            "Students": Student.query.count(),
            "Teachers": Teacher.query.count(),
            "Coordinators": Coordinator.query.count(),
            "Principals": Principal.query.count(),
            "Batches/Sections": Batch.query.count(),
            "Houses": House.query.count(),
            "Classrooms": Classroom.query.count(),
            "Subject Masters": SubjectMaster.query.count(),
            "Total Users": User.query.count(),
        }
        
        print("\n📊 DATABASE STATISTICS:")
        for key, count in stats.items():
            print(f"   • {key}: {count}")
        
        print("\n🏫 ORGANIZATION LOGIN (step 1):")
        print(f"   Name:     {DEFAULT_ORG_NAME}")
        print(f"   Slug:     {DEFAULT_ORG_SLUG}")
        print(f"   Password: {DEFAULT_ORG_PASSWORD}")

        print("\n🎯 USER CREDENTIALS (step 2 — after organization login):")
        print("   Admin:       admin@school.edu / admin123")
        print("   Principal:   principal@school.edu / principal123")
        print("   Coordinator: anjali@school.edu / coordinator123")
        print("   Teacher:     priya.sharma@school.edu / teacher123")

        print("\n🚀 Ready to start the application!\n")


if __name__ == "__main__":
    seed_database()
