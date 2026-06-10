"""Seed a large DEMO ORGANIZATION alongside existing data (non-destructive).

Creates "Greenfield International School" with:
  ~3,000 students (each with a login)  |  120 teachers  |  4 coordinators
  2 admins  |  1 principal  |  2 parents

Run inside the backend container:
    python seed_demo_org.py
"""

import sys
sys.path.insert(0, '.')

import math
import random
from datetime import date

from app import create_app
from models import (
    db, User, Batch, Subject, Teacher, SchoolConfig, Student, Classroom,
    Principal, Coordinator, Organization, Charge, Guardian,
)
from werkzeug.security import generate_password_hash

# Reuse the realistic name/subject catalogs from the main seed (import only —
# importing seed_realistic never runs its destructive seeding).
from seed_realistic import (
    FIRST_NAMES_MALE, FIRST_NAMES_FEMALE, LAST_NAMES, SUBJECTS_DATA,
)

random.seed(42)  # reproducible demo data

ORG_NAME = "Greenfield International School"
ORG_SLUG = "greenfield-international"
ORG_PASSWORD = "greenfield123"
DOMAIN = "greenfield.edu"

PASSWORDS = {
    "admin": "admin123",
    "principal": "principal123",
    "coordinator": "coordinator123",
    "teacher": "teacher123",
    "student": "student123",
    "parent": "parent123",
}

# ~2,964 students total.
CLASS_DISTRIBUTION = {
    "Nursery": {"sections": ["A", "B", "C"], "count": 96},
    "LKG": {"sections": ["A", "B", "C"], "count": 96},
    "UKG": {"sections": ["A", "B", "C"], "count": 96},
    "1": {"sections": ["A", "B", "C", "D", "E"], "count": 190},
    "2": {"sections": ["A", "B", "C", "D", "E"], "count": 190},
    "3": {"sections": ["A", "B", "C", "D", "E"], "count": 190},
    "4": {"sections": ["A", "B", "C", "D", "E"], "count": 190},
    "5": {"sections": ["A", "B", "C", "D", "E"], "count": 190},
    "6": {"sections": ["A", "B", "C", "D", "E"], "count": 210},
    "7": {"sections": ["A", "B", "C", "D", "E"], "count": 210},
    "8": {"sections": ["A", "B", "C", "D", "E"], "count": 210},
    "9": {"sections": ["A", "B", "C", "D", "E", "F"], "count": 288},
    "10": {"sections": ["A", "B", "C", "D", "E", "F"], "count": 288},
    "11 Science": {"sections": ["A", "B"], "count": 128},
    "11 Commerce": {"sections": ["A"], "count": 70},
    "11 Humanities": {"sections": ["A"], "count": 62},
    "12 Science": {"sections": ["A", "B"], "count": 128},
    "12 Commerce": {"sections": ["A"], "count": 70},
    "12 Humanities": {"sections": ["A"], "count": 62},
}

LAB_SUBJECTS = {"Computer Science", "Physics", "Chemistry", "Biology"}
PERIODS_BY_TYPE = {"Core": 5, "Language": 4, "Practical": 4, "PrePrimary": 4, "Activity": 2}

ROOMS = [
    ("GF-LAB1", "Physics Lab", 48, "lab"),
    ("GF-LAB2", "Chemistry Lab", 48, "lab"),
    ("GF-LAB3", "Biology Lab", 48, "lab"),
    ("GF-LAB4", "Computer Lab", 50, "lab"),
    ("GF-LIB", "Central Library", 140, "library"),
    ("GF-MUS", "Music Room", 40, "music"),
    ("GF-ART", "Art Studio", 40, "art"),
    ("GF-GND", "Sports Ground", 400, "ground"),
    ("GF-HALL", "Auditorium", 600, "hall"),
]


def _name():
    first = random.choice(FIRST_NAMES_MALE if random.random() < 0.5 else FIRST_NAMES_FEMALE)
    return f"{first} {random.choice(LAST_NAMES)}"


def _dob_for(grade):
    if grade in ("Nursery", "LKG", "UKG"):
        years = (2022, 2023)
    elif grade in ("1", "2", "3", "4", "5"):
        years = (2018, 2020)
    elif grade in ("6", "7", "8"):
        years = (2015, 2017)
    elif grade in ("9", "10"):
        years = (2013, 2015)
    else:
        years = (2008, 2010)
    return date(random.randint(*years), random.randint(1, 12), random.randint(1, 28))


def seed_demo_org():
    app = create_app()
    with app.app_context():
        if Organization.query.filter_by(slug=ORG_SLUG).first():
            print(f"❌ Organization '{ORG_SLUG}' already exists — aborting (nothing touched).")
            print("   Delete it first if you want to reseed.")
            return

        # ------------------------------------------------------------ org ----
        print(f"🏫 Creating organization: {ORG_NAME}")
        org = Organization(
            name=ORG_NAME,
            slug=ORG_SLUG,
            password_hash=generate_password_hash(ORG_PASSWORD),
            description="Large demo school: ~3,000 students, 120 teachers.",
            school_code="GFIS",
            official_email=f"office@{DOMAIN}",
            academic_year="2026-2027",
            is_active=True,
            logo_url="/scheduler-logo.png",
        )
        db.session.add(org)
        db.session.flush()
        org_id = org.id

        db.session.add(SchoolConfig(
            organization_id=org_id,
            start_time="08:00", end_time="14:00",
            lunch_start="11:00", lunch_end="11:45",
            period_duration=45, periods_per_day=8,
            has_lunch_break=True, working_days=5,
            target_contact_periods_per_week=40,
            class_teacher_hours_per_week=5,
        ))
        db.session.commit()
        print(f"   ✅ org id={org_id} | slug={ORG_SLUG} | password={ORG_PASSWORD}")

        # -------------------------------------------------------- batches ----
        def day_len(grade):
            if grade in ("Nursery", "LKG", "UKG"):
                return 4
            if grade in ("1", "2", "3", "4", "5"):
                return 6
            return 8

        batches = []
        for grade, gd in CLASS_DISTRIBUTION.items():
            per_section = gd["count"] // len(gd["sections"])
            for section in gd["sections"]:
                b = Batch(organization_id=org_id, grade=grade, section=section,
                          student_count=per_section, periods_per_day=day_len(grade))
                db.session.add(b)
                batches.append(b)
        db.session.commit()
        print(f"   ✅ {len(batches)} sections")

        # ------------------------------------------------------- subjects ----
        grade_to_batches = {}
        for b in batches:
            grade_to_batches.setdefault(b.grade, []).append(b)

        subjects, subject_by_name = [], {}
        for _sid, name, _code, stype, applicable in SUBJECTS_DATA:
            applicable_batches = []
            for g in applicable:
                applicable_batches.extend(grade_to_batches.get(g, []))
            is_lab = name in LAB_SUBJECTS
            s = Subject(
                organization_id=org_id, name=name,
                periods_per_week=PERIODS_BY_TYPE.get(stype, 3),
                max_periods_per_day=2 if is_lab else 1,
                requires_double=is_lab,
                batch_ids=[b.id for b in applicable_batches],
            )
            db.session.add(s)
            subjects.append(s)
            subject_by_name[name] = s
        db.session.commit()
        for b in batches:
            b.subject_ids = [s.id for s in subjects if b.id in (s.batch_ids or [])]
        db.session.commit()
        print(f"   ✅ {len(subjects)} subjects wired to sections")

        # ---------------------------------------------------------- rooms ----
        for code, rname, cap, rtype in ROOMS:
            db.session.add(Classroom(organization_id=org_id, room_id=code,
                                     room_name=rname, capacity=cap, room_type=rtype))
        db.session.commit()

        # ------------------------------------------------- management -------
        print("👔 Creating admins / principal / coordinators...")
        def make_user(name, email, role, password):
            u = User(organization_id=org_id, name=name, email=email, role=role,
                     password_hash=generate_password_hash(password))
            db.session.add(u)
            return u

        admins = [
            make_user("Rohit Malhotra", f"admin1@{DOMAIN}", "admin", PASSWORDS["admin"]),
            make_user("Shalini Gupta", f"admin2@{DOMAIN}", "admin", PASSWORDS["admin"]),
        ]
        principal_user = make_user("Dr. Kavita Krishnan", f"principal@{DOMAIN}",
                                   "principal", PASSWORDS["principal"])
        db.session.commit()
        db.session.add(Principal(
            principal_id="GF-P01", user_id=principal_user.id, name=principal_user.name,
            qualification="PhD Education", experience_years=24,
            email=principal_user.email, joining_date=date(2012, 4, 1), phone="9810000001",
        ))

        coordinator_specs = [
            ("Anita Menon", f"anita.menon@{DOMAIN}", "Pre-Primary Coordinator", "Nursery–UKG"),
            ("Suresh Iyer", f"suresh.iyer@{DOMAIN}", "Primary Coordinator", "Classes 1–5"),
            ("Farah Khan", f"farah.khan@{DOMAIN}", "Middle School Coordinator", "Classes 6–8"),
            ("Devika Nair", f"devika.nair@{DOMAIN}", "Senior Coordinator", "Classes 9–12"),
        ]
        for i, (cname, cemail, desig, resp) in enumerate(coordinator_specs, start=1):
            cu = make_user(cname, cemail, "coordinator", PASSWORDS["coordinator"])
            db.session.commit()
            db.session.add(Coordinator(
                coordinator_id=f"GF-C{i:02d}", user_id=cu.id, name=cname,
                designation=desig, responsibility=resp, email=cemail,
                phone=f"98100000{i + 1:02d}",
            ))
        db.session.commit()
        print("   ✅ 2 admins, 1 principal, 4 coordinators")

        # ------------------------------------------------------- teachers ----
        print("👨‍🏫 Creating 120 teachers...")
        pre_primary_subjects = [s for s in subjects
                                if subject_by_name.get(s.name) and
                                any(g in ("Nursery", "LKG", "UKG")
                                    for g in next(a for a in SUBJECTS_DATA if a[1] == s.name)[4])]
        prt_subject_names = ["English", "Hindi", "Mathematics", "Science", "GK", "Art", "Music", "Physical Education"]
        tgt_subject_names = ["English", "Hindi", "Mathematics", "Science", "Physics", "Chemistry",
                             "Biology", "Social Science", "Sanskrit", "Computer Science",
                             "Physical Education", "Art", "Music"]
        pgt_subject_names = ["Physics", "Chemistry", "Biology", "Mathematics", "English",
                             "Computer Science", "Economics", "Accountancy", "Business Studies",
                             "History", "Geography", "Political Science"]
        specialist_names = ["Physical Education"] * 4 + ["Art"] * 3 + ["Music"] * 3 + ["GK"] * 2

        teacher_hash = generate_password_hash(PASSWORDS["teacher"])  # shared (demo)
        teachers = []
        tnum = 0

        def add_teacher(subject_names, designation):
            nonlocal tnum
            tnum += 1
            name = _name()
            email = f"t{tnum}@{DOMAIN}"
            u = User(organization_id=org_id, name=name, email=email, role="teacher",
                     password_hash=teacher_hash)
            db.session.add(u)
            db.session.flush()
            sids = [subject_by_name[n].id for n in subject_names if n in subject_by_name]
            t = Teacher(
                organization_id=org_id, user_id=u.id,
                teacher_code=f"GF-TCH{tnum:04d}", name=name, email=email,
                subject_ids=sids, assigned_batch_ids=[],
                takes_classes=True, max_periods_per_week=35,
            )
            db.session.add(t)
            teachers.append(t)
            return t

        # 9 NTT homeroom teachers (one per pre-primary section)
        ntt = [add_teacher([s.name for s in pre_primary_subjects], "NTT") for _ in range(9)]
        # 30 PRT (classes 1–5)
        prt = [add_teacher([prt_subject_names[i % len(prt_subject_names)]], "PRT") for i in range(30)]
        # 45 TGT (classes 6–10)
        tgt = [add_teacher([tgt_subject_names[i % len(tgt_subject_names)]], "TGT") for i in range(45)]
        # 24 PGT (classes 11–12)
        pgt = [add_teacher([pgt_subject_names[i % len(pgt_subject_names)]], "PGT") for i in range(24)]
        # 12 specialists
        spc = [add_teacher([specialist_names[i]], "SPC") for i in range(12)]
        db.session.commit()
        print(f"   ✅ {len(teachers)} teachers (t1@{DOMAIN} … t{tnum}@{DOMAIN})")

        # ------------------------------------------- class-teacher mapping ---
        pre_sections = [b for b in batches if b.grade in ("Nursery", "LKG", "UKG")]
        prim_sections = [b for b in batches if b.grade in ("1", "2", "3", "4", "5")]
        mid_sections = [b for b in batches if b.grade in ("6", "7", "8", "9", "10")]
        sen_sections = [b for b in batches if b.grade.startswith(("11", "12"))]

        def set_class_teachers(pool, sections):
            for i, b in enumerate(sections):
                if i >= len(pool):
                    break
                t = pool[i]
                t.is_class_teacher = True
                t.class_teacher_batch_id = b.id
                if b.id not in (t.assigned_batch_ids or []):
                    t.assigned_batch_ids = list(t.assigned_batch_ids or []) + [b.id]
                # Homeroom for pre-primary single-teacher mode.
                if b.grade in ("Nursery", "LKG", "UKG"):
                    b.homeroom_teacher_id = t.id

        set_class_teachers(ntt, pre_sections)
        set_class_teachers(prt, prim_sections)
        set_class_teachers(tgt, mid_sections)
        set_class_teachers(pgt, sen_sections)
        db.session.commit()

        # -------------------------------------- coverage + assignments -------
        print("🔗 Ensuring every (section, subject) has an eligible teacher...")
        teachers_for_subject = {s.id: [] for s in subjects}
        for t in teachers:
            for sid in (t.subject_ids or []):
                if sid in teachers_for_subject:
                    teachers_for_subject[sid].append(t)

        batches_per_subject = {s.id: 0 for s in subjects}
        for b in batches:
            for sid in (b.subject_ids or []):
                batches_per_subject[sid] += 1

        TEACHER_BUDGET = 22
        rr = 0
        for s in subjects:
            demand = (s.periods_per_week or 1) * batches_per_subject.get(s.id, 0)
            needed = max(1, math.ceil(demand / TEACHER_BUDGET))
            guard = 0
            while len(teachers_for_subject[s.id]) < needed and guard < len(teachers) * 2:
                t = teachers[rr % len(teachers)]
                rr += 1
                guard += 1
                if t not in teachers_for_subject[s.id]:
                    if s.id not in (t.subject_ids or []):
                        t.subject_ids = list(t.subject_ids or []) + [s.id]
                    teachers_for_subject[s.id].append(t)

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

        # Structured teaching assignments + capability + capacity.
        batch_by_id = {b.id: b for b in batches}
        TARGET, CT_HOURS = 40, 5
        for t in teachers:
            assigned = list(t.assigned_batch_ids or [])
            assignments, grade_caps = [], {}
            for sid in (t.subject_ids or []):
                bids = [bid for bid in assigned
                        if batch_by_id.get(bid) and sid in (batch_by_id[bid].subject_ids or [])]
                if bids:
                    assignments.append({"subject_id": sid, "batch_ids": sorted(set(bids))})
                    grade_caps[sid] = {str(batch_by_id[bid].grade) for bid in bids}
            t.teaching_assignments = assignments
            # Capability is per base grade, not per stream: an English PGT for
            # "12 Science" can teach English to "12 Commerce" too. Widening this
            # gives every senior block more than one possible cover teacher.
            all_grades = {str(b.grade) for b in batches}
            for sid, g in grade_caps.items():
                widened = set(g)
                for gr in g:
                    base = str(gr).split()[0]
                    if base in ("11", "12"):
                        widened |= {ag for ag in all_grades if ag.split()[0] == base}
                grade_caps[sid] = widened
            t.subject_grades = [{"subject_id": sid, "grades": sorted(g)} for sid, g in grade_caps.items()]
            t.charges = []
            t.max_periods_per_week = TARGET - (CT_HOURS if t.is_class_teacher else 0)
        db.session.commit()

        # Departments / charges catalog (a couple of teachers carry duties).
        num_ct = sum(1 for t in teachers if t.is_class_teacher)
        for cname, hours, req, takes in [
            ("Class Teacher", CT_HOURS, max(1, num_ct), True),
            ("Library", 0, 2, False),
            ("Club", 2, 10, True),
            ("Exam Cell", 3, 4, True),
        ]:
            db.session.add(Charge(organization_id=org_id, name=cname,
                                  default_hours_per_week=hours,
                                  members_required=req, takes_classes=takes))
        db.session.commit()
        print("   ✅ coverage + structured assignments + charge catalog")

        # ------------------------------------------------------- students ----
        print("👨‍🎓 Creating ~3,000 students (each with a login)...")
        student_hash = generate_password_hash(PASSWORDS["student"])  # shared (demo)
        batch_of = {(b.grade, b.section): b for b in batches}
        count = 0
        admission = 250001
        sample_students = []

        for grade, gd in CLASS_DISTRIBUTION.items():
            per_section = gd["count"] // len(gd["sections"])
            for section in gd["sections"]:
                b = batch_of[(grade, section)]
                for roll in range(1, per_section + 1):
                    count += 1
                    is_male = random.random() < 0.5
                    first = random.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
                    last = random.choice(LAST_NAMES)
                    code = f"GF-STU{count:05d}"
                    email = f"s{count:05d}@{DOMAIN}"

                    u = User(organization_id=org_id, name=f"{first} {last}", email=email,
                             role="student", password_hash=student_hash, batch_id=b.id)
                    db.session.add(u)
                    db.session.flush()

                    st = Student(
                        organization_id=org_id,
                        student_id=code,
                        admission_no=f"GF{admission}",
                        user_id=u.id,
                        first_name=first, last_name=last, email=email,
                        gender="Male" if is_male else "Female",
                        date_of_birth=_dob_for(grade),
                        class_grade=grade, section=section, roll_no=roll,
                        father_name=f"Mr. {last}",
                        mother_name=f"Mrs. {random.choice(FIRST_NAMES_FEMALE)} {last}",
                        contact_number="98" + "".join(str(random.randint(0, 9)) for _ in range(8)),
                        address=random.choice(["New Delhi", "Noida", "Gurgaon", "Faridabad", "Ghaziabad"]),
                        transport_mode=random.choice(["Bus", "Private", "Walk"]),
                        blood_group=random.choice(["A+", "B+", "O+", "AB+", "A-", "O-"]),
                        admission_date=date(2026, 4, 1),
                        status="Active",
                        consent_given=True,
                    )
                    db.session.add(st)
                    admission += 1

                    if count <= 3:
                        sample_students.append((f"{first} {last}", f"{grade}-{section}", email))
                    if count % 500 == 0:
                        db.session.commit()
                        print(f"   [{count}] ...")
        db.session.commit()
        print(f"   ✅ {count} students")

        # -------------------------------------------------------- parents ----
        print("👪 Creating 2 parent accounts...")
        first_students = Student.query.filter_by(organization_id=org_id).order_by(Student.id).limit(4).all()
        for i in (1, 2):
            pu = make_user(f"Parent Demo {i}", f"parent{i}@{DOMAIN}", "parent", PASSWORDS["parent"])
            db.session.commit()
            for child in first_students[(i - 1) * 2: i * 2]:
                db.session.add(Guardian(organization_id=org_id, user_id=pu.id,
                                        student_id=child.id, relation="guardian"))
        db.session.commit()

        # -------------------------------------------------------- summary ----
        print("\n" + "=" * 70)
        print("✅ GREENFIELD DEMO ORGANIZATION SEEDED")
        print("=" * 70)
        print(f"Sections: {len(batches)} | Teachers: {len(teachers)} | Students: {count}")
        print(f"\n🏫 ORGANIZATION LOGIN (step 1):")
        print(f"   Name/slug: {ORG_NAME}  ({ORG_SLUG})")
        print(f"   Password:  {ORG_PASSWORD}")
        print(f"\n🎯 USER LOGINS (step 2):")
        print(f"   Admins:       admin1@{DOMAIN} / admin2@{DOMAIN}  — {PASSWORDS['admin']}")
        print(f"   Principal:    principal@{DOMAIN}  — {PASSWORDS['principal']}")
        print(f"   Coordinators: anita.menon@ / suresh.iyer@ / farah.khan@ / devika.nair@{DOMAIN}  — {PASSWORDS['coordinator']}")
        print(f"   Teachers:     t1@{DOMAIN} … t120@{DOMAIN}  — {PASSWORDS['teacher']}")
        print(f"   Students:     s00001@{DOMAIN} … s{count:05d}@{DOMAIN}  — {PASSWORDS['student']}")
        print(f"   Parents:      parent1@{DOMAIN} / parent2@{DOMAIN}  — {PASSWORDS['parent']}")
        for nm, cls, em in sample_students:
            print(f"      e.g. {em}  ({nm}, {cls})")


if __name__ == "__main__":
    seed_demo_org()
