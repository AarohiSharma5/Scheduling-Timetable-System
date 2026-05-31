"""One-off backfill for the extended teacher profile fields.

Fills the new columns (gender, experience_years, availability, status,
primary_subject, secondary_subject) for teachers that don't have them yet,
WITHOUT overwriting any value already present. Primary/secondary subject are
derived from each teacher's real capability (teaching_assignments /
subject_grades / subject_ids) so they reflect what they actually teach;
gender/experience are plausible synthetic values for the sample dataset.

Run:  docker compose exec -T backend python backfill_teachers.py
"""
import random

from app import create_app
from models import db, Teacher, Subject


FEMALE_HINTS = {
    "priya", "neha", "pooja", "anjali", "ritika", "sonal", "kavya", "maya",
    "amita", "sunita", "geeta", "rekha", "shreya", "divya", "meena", "asha",
    "nisha", "anita", "deepa", "swati", "preeti", "kiran", "radha",
}


def guess_gender(name):
    first = (name or "").strip().split(" ")[0].lower()
    if first in FEMALE_HINTS:
        return "Female"
    # default split for the rest of the sample data
    return random.choice(["Male", "Female"])


def main():
    app = create_app()
    with app.app_context():
        subjects = {s.id: s.name for s in Subject.query.all()}
        teachers = Teacher.query.all()
        changed = 0

        for t in teachers:
            touched = False

            if not t.gender:
                t.gender = guess_gender(t.name)
                touched = True

            if t.experience_years is None:
                t.experience_years = random.randint(1, 25)
                touched = True

            if not t.availability:
                t.availability = "Part-time" if random.random() < 0.12 else "Full-time"
                touched = True

            if not t.status:
                t.status = "active"
                touched = True

            # Derive primary/secondary subject from real capability.
            cap_subject_ids = []
            for a in (t.teaching_assignments or []):
                sid = a.get("subject_id")
                if sid and sid not in cap_subject_ids:
                    cap_subject_ids.append(sid)
            for a in (t.subject_grades or []):
                sid = a.get("subject_id")
                if sid and sid not in cap_subject_ids:
                    cap_subject_ids.append(sid)
            for sid in (t.subject_ids or []):
                if sid not in cap_subject_ids:
                    cap_subject_ids.append(sid)

            names = [subjects.get(sid) for sid in cap_subject_ids if subjects.get(sid)]
            if not t.primary_subject and names:
                t.primary_subject = names[0]
                touched = True
            if not t.secondary_subject and len(names) > 1:
                t.secondary_subject = names[1]
                touched = True

            if touched:
                changed += 1

        db.session.commit()
        print(f"Backfilled {changed}/{len(teachers)} teachers.")


if __name__ == "__main__":
    main()
