"""
Database Seeding Script
Initializes the database with sample data for testing
"""

import os
import sys
sys.path.insert(0, '.')

from app import create_app
from models import db, User, Batch, Subject, Teacher, SchoolConfig, Timetable, TimetableSlot
from datetime import datetime
from werkzeug.security import generate_password_hash


def seed_database():
    """Populate the database with sample data"""
    
    app = create_app()
    with app.app_context():
        # Drop all tables and recreate
        print("⚠️  Dropping all tables...")
        db.drop_all()
        
        print("📊 Creating all tables...")
        db.create_all()
        
        # ===================================================================
        # 1. SCHOOL CONFIGURATION
        # ===================================================================
        print("⚙️  Setting up school configuration...")
        school_config = SchoolConfig(
            id=1,
            start_time="08:00",
            end_time="15:00",
            lunch_start="12:00",
            lunch_end="13:00",
            period_duration=45,
            periods_per_day=6,
            working_days=5,
        )
        db.session.add(school_config)
        db.session.commit()
        print("   ✅ School config created: 8:00 AM - 3:00 PM, 6 periods × 45 min")
        
        # ===================================================================
        # 2. BATCHES (Grades & Sections)
        # ===================================================================
        print("\n📚 Creating batches...")
        batches = []
        batch_configs = [
            ("9", "A", 45),
            ("9", "B", 42),
            ("10", "A", 48),
            ("10", "B", 46),
            ("11", "A", 40),
            ("12", "A", 38),
        ]
        
        for grade, section, student_count in batch_configs:
            batch = Batch(grade=grade, section=section, student_count=student_count)
            db.session.add(batch)
            batches.append(batch)
        
        db.session.commit()
        print(f"   ✅ Created {len(batches)} batches")
        
        # ===================================================================
        # 3. SUBJECTS
        # ===================================================================
        print("\n📖 Creating subjects...")
        subjects_data = [
            ("English", 4),
            ("Mathematics", 4),
            ("Physics", 3),
            ("Chemistry", 3),
            ("Biology", 2),
            ("History", 3),
            ("Geography", 2),
            ("Civics", 2),
            ("Physical Education", 2),
            ("Computer Science", 2),
        ]
        
        subjects = []
        for name, periods in subjects_data:
            subject = Subject(name=name, periods_per_week=periods)
            # Assign to relevant batches
            subject.batch_ids = [b.id for b in batches[:4]]  # All grades 9-10
            db.session.add(subject)
            subjects.append(subject)
        
        db.session.commit()
        print(f"   ✅ Created {len(subjects)} subjects")
        
        # Update batches to include subject IDs
        for batch in batches:
            batch.subject_ids = [s.id for s in subjects]
        db.session.commit()
        
        # ===================================================================
        # 4. USERS & TEACHERS
        # ===================================================================
        print("\n👨‍🏫 Creating users and teachers...")
        
        # Admin User
        admin_user = User(
            name="School Admin",
            email="admin@school.edu",
            role="admin",
            password_hash=generate_password_hash("admin123"),
        )
        db.session.add(admin_user)
        
        # Principal User
        principal_user = User(
            name="Dr. Rajesh Sharma",
            email="principal@school.edu",
            role="principal",
            password_hash=generate_password_hash("principal123"),
        )
        db.session.add(principal_user)
        
        db.session.commit()
        
        # Teachers
        teachers_data = [
            ("Priya Verma", "priya.verma@school.edu", ["English"], [batches[0].id, batches[2].id], True, batches[0].id, False),
            ("Rajesh Kumar", "rajesh.kumar@school.edu", ["Mathematics"], [batches[0].id, batches[1].id, batches[2].id], True, batches[1].id, False),
            ("Anjali Singh", "anjali.singh@school.edu", ["Physics", "Chemistry"], [batches[2].id, batches[3].id], False, None, False),
            ("Vikram Patel", "vikram.patel@school.edu", ["Biology"], [batches[2].id, batches[3].id], False, None, True),  # Has duties
            ("Meera Desai", "meera.desai@school.edu", ["History", "Geography"], [batches[0].id, batches[1].id], False, None, False),
            ("Arjun Nair", "arjun.nair@school.edu", ["Physical Education"], [batches[0].id, batches[1].id, batches[2].id, batches[3].id], False, None, True),  # Has duties
            ("Pooja Gupta", "pooja.gupta@school.edu", ["Computer Science"], [batches[2].id, batches[3].id], False, None, False),
            ("Sanjay Rao", "sanjay.rao@school.edu", ["Civics"], [batches[0].id, batches[1].id, batches[2].id], False, None, False),
        ]
        
        teachers = []
        for name, email, subject_names, assigned_batches, is_class_teacher, class_batch, has_duties in teachers_data:
            teacher_user = User(
                name=name,
                email=email,
                role="teacher",
                password_hash=generate_password_hash("teacher123"),
            )
            db.session.add(teacher_user)
            db.session.commit()
            
            # Map subject names to IDs
            subject_ids = [s.id for s in subjects if s.name in subject_names]
            
            # Calculate max periods based on duties
            max_periods = 24 if not has_duties else int(24 * 0.6)  # 60% if has duties
            
            teacher = Teacher(
                user_id=teacher_user.id,
                name=name,
                email=email,
                subject_ids=subject_ids,
                assigned_batch_ids=assigned_batches,
                is_class_teacher=is_class_teacher,
                class_teacher_batch_id=class_batch,
                has_duties=has_duties,
                max_periods_per_week=max_periods,
            )
            db.session.add(teacher)
            teachers.append(teacher)
        
        db.session.commit()
        print(f"   ✅ Created admin, principal, and {len(teachers)} teachers")
        
        # ===================================================================
        # 5. STUDENTS
        # ===================================================================
        print("\n👨‍🎓 Creating student users...")
        
        students = []
        for batch in batches:
            for i in range(3):  # Add 3 sample students per batch
                student_user = User(
                    name=f"Student {i+1} - {batch.grade}{batch.section}",
                    email=f"student{batch.grade}{batch.section}{i+1}@school.edu",
                    role="student",
                    batch_id=batch.id,
                    password_hash=generate_password_hash("student123"),
                )
                db.session.add(student_user)
                students.append(student_user)
        
        db.session.commit()
        print(f"   ✅ Created {len(students)} student accounts")
        
        # ===================================================================
        # 6. SAMPLE TIMETABLE WITH SLOTS
        # ===================================================================
        print("\n📅 Creating sample timetable with full schedule...")
        timetable = Timetable(
            name="Week 1 - May 2026",
            description="Sample timetable for demonstration",
            status="published",  # Published so teachers can see it
            warnings=[],
        )
        db.session.add(timetable)
        db.session.flush()  # Get the ID
        
        print(f"   📌 Created timetable ID: {timetable.id}")
        print(f"   🧑‍🏫 Teachers available: {len(teachers)}")
        print(f"   📚 Subjects available: {len(subjects)}")
        print(f"   🏫 Batches available: {len(batches)}")
        
        # Validate data before creating slots
        try:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            
            # Create simple schedule for all 5 days
            simple_schedule = [
                # Monday: English, Math, Physics, Lunch, History, PE
                [(teachers[0], subjects[0], batches[0]),
                 (teachers[1], subjects[1], batches[0]),
                 (teachers[2], subjects[2], batches[2]),
                 None,
                 (teachers[4], subjects[5], batches[0]),
                 (teachers[5], subjects[8], batches[0])],
                # Tuesday: Math, Chemistry, CS, Lunch, English, Civics
                [(teachers[1], subjects[1], batches[0]),
                 (teachers[2], subjects[3], batches[2]),
                 (teachers[6], subjects[9], batches[2]),
                 None,
                 (teachers[0], subjects[0], batches[0]),
                 (teachers[7], subjects[7], batches[0])],
                # Wednesday: Physics, Biology, English, Lunch, Math, PE
                [(teachers[2], subjects[2], batches[2]),
                 (teachers[3], subjects[4], batches[2]),
                 (teachers[0], subjects[0], batches[0]),
                 None,
                 (teachers[1], subjects[1], batches[0]),
                 (teachers[5], subjects[8], batches[0])],
                # Thursday: History, CS, Math, Lunch, Chemistry, Civics
                [(teachers[4], subjects[5], batches[0]),
                 (teachers[6], subjects[9], batches[2]),
                 (teachers[1], subjects[1], batches[0]),
                 None,
                 (teachers[2], subjects[3], batches[2]),
                 (teachers[7], subjects[7], batches[0])],
                # Friday: English, Biology, Geography, Lunch, CS, PE
                [(teachers[0], subjects[0], batches[0]),
                 (teachers[3], subjects[4], batches[2]),
                 (teachers[4], subjects[6], batches[0]),
                 None,
                 (teachers[6], subjects[9], batches[2]),
                 (teachers[5], subjects[8], batches[0])],
            ]
            
            slot_count = 0
            for day_idx, day_name in enumerate(day_names):
                for period_idx, slot_data in enumerate(simple_schedule[day_idx]):
                    if slot_data is None:
                        # Lunch period
                        slot = TimetableSlot(
                            timetable_id=timetable.id,
                            day=day_name,
                            period_number=period_idx + 1,
                            batch_id=None,
                            teacher_id=None,
                            subject_id=None,
                            is_lunch=True,
                        )
                    else:
                        teacher_obj, subject_obj, batch_obj = slot_data
                        slot = TimetableSlot(
                            timetable_id=timetable.id,
                            day=day_name,
                            period_number=period_idx + 1,
                            batch_id=batch_obj.id,
                            teacher_id=teacher_obj.id,
                            subject_id=subject_obj.id,
                            is_lunch=False,
                        )
                    
                    db.session.add(slot)
                    slot_count += 1
                    
            db.session.commit()
            print(f"   ✅ Generated {slot_count} timetable slots (5 days × 6 periods)")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error creating timetable slots: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # ===================================================================
        # SUMMARY
        # ===================================================================
        print("\n" + "=" * 60)
        print("✅ DATABASE SEEDING COMPLETE!")
        print("=" * 60)
        print("\n📋 TEST ACCOUNTS:\n")
        print("  ADMIN:")
        print("    Email: admin@school.edu")
        print("    Password: admin123")
        print("\n  PRINCIPAL:")
        print("    Email: principal@school.edu")
        print("    Password: principal123")
        print("\n  TEACHER (Sample):")
        print("    Email: priya.verma@school.edu")
        print("    Password: teacher123")
        print("\n  STUDENT (Sample):")
        print(f"    Email: student9A1@school.edu")
        print("    Password: student123")
        print("\n" + "=" * 60)
        print(f"\n📊 DATABASE SUMMARY:")
        print(f"   • Batches: {len(batches)}")
        print(f"   • Subjects: {len(subjects)}")
        print(f"   • Teachers: {len(teachers)}")
        print(f"   • Students: {len(students)}")
        print(f"   • Total Users: {len(teachers) + len(students) + 2}")  # +2 for admin/principal
        print("\n🚀 Ready to start the application!\n")


if __name__ == "__main__":
    seed_database()
