"""Student admission helpers: ID generation, section balancing, roll numbering.

Kept separate from routes.py so the (testable) business rules don't get buried
in the HTTP layer:

  * unique, human-readable student & admission codes
  * "send the new student to the lowest-strength section" balancing
  * alphabetical roll-number (re)sequencing inside a section

All counts/queries are organization-scoped where it matters; the unique codes
are derived from the global max suffix because ``student_id`` / ``admission_no``
are globally unique columns.
"""

from datetime import date

from models import db, Student, Batch

# How many students a single section can hold before it's considered "full".
DEFAULT_SECTION_CAPACITY = 45
# Seats we try to keep free in each section for future admissions. Auto-placement
# prefers sections below (capacity - buffer); it will still overflow if every
# section is full rather than refuse the admission.
DEFAULT_ADMISSION_BUFFER = 2

# Statuses that mean the student still occupies a seat / roll number.
ACTIVE_STATUSES = {"active"}


def _max_suffix(prefix):
    """Largest integer suffix currently used by codes starting with ``prefix``.

    Scans globally (codes are globally unique) and tolerates mixed widths/years.
    Returns 0 when no code exists yet.
    """
    best = 0
    rows = db.session.query(Student.student_id, Student.admission_no).all()
    col = 0 if prefix == "STU" else 1
    for row in rows:
        code = row[col]
        if not code or not code.startswith(prefix):
            continue
        digits = "".join(ch for ch in code[len(prefix):] if ch.isdigit())
        if digits:
            best = max(best, int(digits))
    return best


def next_student_code():
    """Next free ``STU0001``-style id (4-padded, grows past 9999 naturally)."""
    nxt = _max_suffix("STU") + 1
    return f"STU{nxt:04d}"


def next_admission_no(today=None):
    """Next free ``ADMyy00001``-style admission number for the current year.

    Format: ``ADM`` + 2-digit year + 5-digit running sequence. The sequence is
    derived from the global max so it never collides with seeded data.
    """
    today = today or date.today()
    yy = today.year % 100
    base = _max_suffix("ADM")
    # If the existing max already encodes this year (>= yy*100000) just +1;
    # otherwise start this year's block.
    year_floor = yy * 100000
    nxt = max(base, year_floor) + 1
    return f"ADM{nxt}"


def _student_name_key(s):
    """Sort key for alphabetical roll ordering: active first, then by name."""
    active = 0 if (s.status or "").strip().lower() in ACTIVE_STATUSES else 1
    return (active, (s.first_name or "").lower(), (s.last_name or "").lower(), s.id or 0)


def sections_for_grade(org_id, class_grade):
    """All section labels that exist for a grade.

    Union of configured Batch sections and any sections that already have
    students, so the balancer never misses a real section.
    """
    secs = set()
    for b in Batch.query.filter_by(organization_id=org_id, grade=str(class_grade)).all():
        if b.section:
            secs.add(b.section)
    rows = (
        db.session.query(Student.section)
        .filter_by(organization_id=org_id, class_grade=str(class_grade))
        .distinct()
        .all()
    )
    for (sec,) in rows:
        if sec:
            secs.add(sec)
    return sorted(secs)


def section_strengths(org_id, class_grade, active_only=True):
    """Map of section -> current student count for a grade."""
    out = {sec: 0 for sec in sections_for_grade(org_id, class_grade)}
    q = Student.query.filter_by(organization_id=org_id, class_grade=str(class_grade))
    for s in q.all():
        if active_only and (s.status or "").strip().lower() not in ACTIVE_STATUSES:
            continue
        out[s.section] = out.get(s.section, 0) + 1
    return out


def choose_section(org_id, class_grade, capacity=DEFAULT_SECTION_CAPACITY,
                   buffer=DEFAULT_ADMISSION_BUFFER):
    """Pick the section a new student should join.

    Strategy (matches the spec example 9A=41, 9B=42, 9C=40 -> new joins 9C):
      * prefer the section with the *lowest* current strength,
      * only among sections still under (capacity - buffer),
      * fall back to the global lowest-strength section (flagged over-capacity)
        if every section is already full.

    Returns ``(section_label, over_capacity)``. If no sections are configured
    yet, defaults to "A".
    """
    strengths = section_strengths(org_id, class_grade)
    if not strengths:
        return "A", False

    soft_cap = max(0, capacity - buffer)
    under = {sec: n for sec, n in strengths.items() if n < soft_cap}
    pool = under or strengths
    over_capacity = not under
    # Lowest strength wins; ties broken alphabetically for stable, predictable output.
    section = min(sorted(pool.keys()), key=lambda sec: pool[sec])
    return section, over_capacity


def resequence_rolls(org_id, class_grade, section):
    """Renumber roll_no 1..N alphabetically for one section (active first).

    Does not commit — the caller owns the transaction.
    """
    students = (
        Student.query.filter_by(
            organization_id=org_id, class_grade=str(class_grade), section=section
        ).all()
    )
    students.sort(key=_student_name_key)
    roll = 0
    for s in students:
        if (s.status or "").strip().lower() in ACTIVE_STATUSES:
            roll += 1
            s.roll_no = roll
        else:
            # Inactive/left students don't hold a live roll number.
            s.roll_no = None
    return len(students)
