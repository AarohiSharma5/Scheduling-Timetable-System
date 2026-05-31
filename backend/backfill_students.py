"""One-off backfill: ensure every existing student has the full attribute set.

Only fills fields that are currently empty — it never overwrites real data and
never touches admission_no / roll_no (those follow their own generation logic).
Random-but-plausible values are used for the sample dataset.

Run:  docker compose exec backend python backfill_students.py
"""

import random
from datetime import date

from app import create_app
from models import db, Student

FIRST_M = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Krishna", "Ishaan", "Kabir", "Ayaan"]
FIRST_F = ["Aanya", "Diya", "Saanvi", "Aadhya", "Pari", "Anika", "Navya", "Myra", "Sara", "Ira"]
LAST = ["Sharma", "Verma", "Gupta", "Patel", "Mehta", "Reddy", "Nair", "Iyer", "Bose", "Kapoor", "Bhatnagar", "Desai"]
CITIES = ["New Delhi", "Noida", "Gurgaon", "Bengaluru", "Mumbai", "Pune", "Chennai", "Hyderabad", "Jaipur", "Lucknow"]
BLOOD = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]


def _phone():
    return "9" + "".join(str(random.randint(0, 9)) for _ in range(9))


def _dob_for_grade(grade):
    g = str(grade)
    if g in ("Nursery", "LKG", "UKG"):
        y = random.randint(2021, 2022)
    elif g in ("1", "2", "3", "4", "5"):
        y = random.randint(2017, 2020)
    elif g in ("6", "7", "8"):
        y = random.randint(2014, 2016)
    elif g in ("9", "10"):
        y = random.randint(2012, 2014)
    else:
        y = random.randint(2007, 2009)
    return date(y, random.randint(1, 12), random.randint(1, 28))


def run():
    app = create_app("production")
    with app.app_context():
        students = Student.query.all()
        filled = 0
        for s in students:
            changed = False
            if not s.gender:
                s.gender = random.choice(["Male", "Female"]); changed = True
            if not s.date_of_birth:
                s.date_of_birth = _dob_for_grade(s.class_grade); changed = True
            if not s.father_name:
                s.father_name = f"Mr. {random.choice(LAST)}"; changed = True
            if not s.mother_name:
                s.mother_name = f"Mrs. {random.choice(FIRST_F)} {random.choice(LAST)}"; changed = True
            if not s.contact_number:
                s.contact_number = _phone(); changed = True
            if not s.address:
                s.address = random.choice(CITIES); changed = True
            if not s.blood_group:
                s.blood_group = random.choice(BLOOD); changed = True
            if not s.admission_date:
                s.admission_date = date(2023, 4, 1); changed = True
            if not s.email:
                fn = (s.first_name or "student").lower()
                ln = (s.last_name or "").lower()
                s.email = f"{fn}.{ln}{s.id}@parentmail.com".replace(" ", "")
                changed = True
            if changed:
                filled += 1
        db.session.commit()
        print(f"Backfilled {filled} of {len(students)} students.")


if __name__ == "__main__":
    run()
