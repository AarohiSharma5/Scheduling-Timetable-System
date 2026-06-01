"""Student-level "no class loss" validation.

Given a generated timetable, verify for every active student that:
  * all their section's COMPULSORY (core) subjects are scheduled,
  * each chosen ELECTIVE / language has a scheduled group slot,
  * none of their periods overlap (a student is never double-booked between a
    core period and an elective block).

Elective group slots are stored with batch_id = NULL and the elective subject;
we map them to a grade via the teaching groups for that subject.
"""

from collections import defaultdict

from models import (
    db, Student, Subject, Batch, TimetableSlot, TeachingGroup,
)
from student_service import ACTIVE_STATUSES


def _norm(s):
    return "".join(ch for ch in str(s or "").lower() if ch.isalnum())


def validate_coverage(org_id, timetable_id):
    subjects = {s.id: s for s in Subject.query.filter_by(organization_id=org_id).all()}
    subj_by_norm = {_norm(s.name): s for s in subjects.values()}
    core_ids = {sid for sid, s in subjects.items() if (s.subject_type or "core") == "core"}

    batches = Batch.query.filter_by(organization_id=org_id).all()
    batch_by_key = {(b.grade, b.section): b for b in batches}

    slots = TimetableSlot.query.filter_by(timetable_id=timetable_id).all()

    # Core presence per section + the periods a section is occupied.
    section_subj = defaultdict(set)         # (grade, section) -> {subject_id}
    section_periods = defaultdict(set)      # (grade, section) -> {(day, period)}
    batch_grade_section = {b.id: (b.grade, b.section) for b in batches}
    # Elective group slots (batch_id NULL): subject_id -> {(day, period)}
    elective_scheduled = defaultdict(set)
    for sl in slots:
        if sl.is_lunch:
            continue
        if sl.batch_id and sl.batch_id in batch_grade_section:
            key = batch_grade_section[sl.batch_id]
            if sl.subject_id:
                section_subj[key].add(sl.subject_id)
            section_periods[key].add((sl.day, sl.period_number))
        elif sl.batch_id is None and sl.subject_id:
            elective_scheduled[sl.subject_id].add((sl.day, sl.period_number))

    # Elective subject -> the periods its block runs (for overlap checks).
    elective_periods_by_subject = {sid: pers for sid, pers in elective_scheduled.items()}

    students = [
        s for s in Student.query.filter_by(organization_id=org_id).all()
        if (s.status or "").strip().lower() in ACTIVE_STATUSES
    ]

    issues = []
    n_missing_core = n_missing_elective = n_overlap = 0
    students_ok = 0

    for stu in students:
        key = (stu.class_grade, stu.section)
        batch = batch_by_key.get(key)
        student_problems = []

        # 1) Compulsory subjects of the section must all be scheduled.
        if batch:
            for sid in (batch.subject_ids or []):
                if sid in core_ids and sid not in section_subj.get(key, set()):
                    student_problems.append(f"core subject '{subjects[sid].name}' not scheduled")

        # 2) Each chosen elective/language must have a scheduled group slot.
        chosen_periods = []
        for name in (stu.elective_subjects or []):
            subj = subj_by_norm.get(_norm(name))
            if not subj:
                continue
            pers = elective_periods_by_subject.get(subj.id)
            if not pers:
                student_problems.append(f"elective '{subj.name}' has no scheduled slot")
            else:
                chosen_periods.append((subj.id, pers))

        # 3) Overlap: an elective block period must not collide with the
        #    student's core section periods (they'd be in two places at once).
        sec_pers = section_periods.get(key, set())
        for sid, pers in chosen_periods:
            clash = pers & sec_pers
            if clash:
                d, p = sorted(clash)[0]
                student_problems.append(f"elective '{subjects[sid].name}' overlaps a class on {d} P{p}")

        if student_problems:
            if any("core subject" in p for p in student_problems):
                n_missing_core += 1
            if any("elective" in p and "no scheduled" in p for p in student_problems):
                n_missing_elective += 1
            if any("overlaps" in p for p in student_problems):
                n_overlap += 1
            if len(issues) < 50:
                issues.append({
                    "student_id": stu.id,
                    "name": f"{stu.first_name} {stu.last_name}".strip(),
                    "class": f"{stu.class_grade}-{stu.section}",
                    "problems": student_problems,
                })
        else:
            students_ok += 1

    return {
        "timetable_id": timetable_id,
        "students_total": len(students),
        "students_ok": students_ok,
        "students_with_issues": len(students) - students_ok,
        "counts": {
            "missing_core": n_missing_core,
            "missing_elective": n_missing_elective,
            "overlaps": n_overlap,
        },
        "ok": students_ok == len(students),
        "issues_sample": issues,
    }
