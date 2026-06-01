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

import re
from collections import defaultdict
from datetime import date

from models import db, Student, Batch, Classroom, SchoolConfig

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


# ---------------------------------------------------------------------------
# Admission-number patterns
# ---------------------------------------------------------------------------
# Auto-generation must *continue an organization's existing format* rather than
# impose our own. We learn the format from the admission numbers already on
# record (seeded, manually entered, or imported), so an org using "ADM240001",
# "2024/001" or "SCH-1001" keeps getting numbers in that same shape.

def _parse_admission(code):
    """Split an admission number into (prefix, number, width, suffix).

    The numeric part is the *last* run of digits; everything before it is the
    prefix, everything after is the suffix. Returns None if there are no digits.
    """
    if not code:
        return None
    m = re.match(r"^(.*?)(\d+)(\D*)$", str(code).strip())
    if not m:
        return None
    prefix, digits, suffix = m.group(1), m.group(2), m.group(3)
    return prefix, int(digits), len(digits), suffix


def detect_admission_pattern(org_id):
    """Infer the dominant admission-number pattern used by an organization.

    Groups existing numbers by (prefix, suffix, digit-width); the group with the
    most members wins (ties broken by highest value). Returns a dict with the
    prefix/suffix/width and the current max number, or None when the org has no
    parseable admission numbers yet.
    """
    codes = [
        s.admission_no
        for s in Student.query.filter_by(organization_id=org_id).all()
        if s.admission_no
    ]
    groups = defaultdict(list)
    for c in codes:
        parsed = _parse_admission(c)
        if parsed:
            prefix, num, width, suffix = parsed
            groups[(prefix, suffix, width)].append(num)
    if not groups:
        return None
    sig = max(groups.keys(), key=lambda k: (len(groups[k]), max(groups[k])))
    prefix, suffix, width = sig
    return {"prefix": prefix, "suffix": suffix, "width": width, "max": max(groups[sig])}


def _format_admission(pat, number):
    return f"{pat['prefix']}{str(number).zfill(pat['width'])}{pat['suffix']}"


def _default_admission_pattern(today=None):
    """Fallback when an org has no admission numbers yet: ADM + yy + 5 digits."""
    today = today or date.today()
    yy = today.year % 100
    return {"prefix": "ADM", "suffix": "", "width": 7, "max": yy * 100000}


def next_admission_no(org_id, today=None):
    """Next admission number, continuing the org's existing pattern."""
    pat = detect_admission_pattern(org_id) or _default_admission_pattern(today)
    return _format_admission(pat, pat["max"] + 1)


def student_code_allocator():
    """Return a function that yields sequential ``STU####`` codes.

    Seeds from the current global max once, then increments in memory — safe for
    bulk inserts within a single transaction (where the DB max won't change
    until commit).
    """
    counter = {"v": _max_suffix("STU")}

    def _next():
        counter["v"] += 1
        return f"STU{counter['v']:04d}"

    return _next


def admission_no_allocator(org_id, today=None):
    """Allocator that yields sequential admission numbers in the org's pattern.

    Seeds from the org's detected pattern (or the default) once, then increments
    in memory — safe for bulk inserts within a single transaction.
    """
    pat = detect_admission_pattern(org_id) or _default_admission_pattern(today)
    counter = {"v": pat["max"]}

    def _next():
        counter["v"] += 1
        return _format_admission(pat, counter["v"])

    return _next


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


def org_default_capacity(org_id):
    """The organization's default per-room/section capacity (config, else 45)."""
    cfg = SchoolConfig.query.filter_by(organization_id=org_id).first()
    if cfg and cfg.default_room_capacity:
        return cfg.default_room_capacity
    return DEFAULT_SECTION_CAPACITY


def section_capacities(org_id, class_grade):
    """Per-section seat capacity for a grade: batch override → home-room → default.

    Returns ``(caps_dict, default_capacity)``.
    """
    default = org_default_capacity(org_id)
    caps = {}
    for b in Batch.query.filter_by(organization_id=org_id, grade=str(class_grade)).all():
        if b.capacity:
            cap = b.capacity
        elif b.room_id:
            room = Classroom.query.get(b.room_id)
            cap = (room.capacity if room and room.capacity else default)
        else:
            cap = default
        caps[b.section] = cap
    return caps, default


def choose_section(org_id, class_grade, capacity=None,
                   buffer=DEFAULT_ADMISSION_BUFFER):
    """Pick the section a new student should join (capacity-aware).

    Strategy (matches the spec example 9A=41, 9B=42, 9C=40 -> new joins 9C):
      * prefer the section with the *lowest* current strength,
      * only among sections still under (capacity - buffer),
      * never choose a section already at its hard capacity unless EVERY section
        is full (in which case ``over_capacity`` is returned True).

    Capacity is per-section (from the batch override / home room / org default).
    Passing an explicit ``capacity`` forces a uniform cap for every section.
    Returns ``(section_label, over_capacity)``; defaults to "A" when no sections.
    """
    strengths = section_strengths(org_id, class_grade)
    if not strengths:
        return "A", False

    caps, default = section_capacities(org_id, class_grade)

    def cap_of(sec):
        if capacity is not None:
            return capacity
        return caps.get(sec, default)

    under_hard = {s: n for s, n in strengths.items() if n < cap_of(s)}
    under_soft = {s: n for s, n in strengths.items() if n < max(0, cap_of(s) - buffer)}
    pool = under_soft or under_hard or strengths
    over_capacity = not under_hard
    # Lowest strength wins; ties broken alphabetically for stable, predictable output.
    section = min(sorted(pool.keys()), key=lambda sec: pool[sec])
    return section, over_capacity


def distribute_grade(org_id, class_grade):
    """Rebalance a grade's active students across its sections within capacity.

    Moves the minimum number of (alphabetically-last) students out of any
    over-capacity section into the section with the most free space, then
    resequences roll numbers everywhere. Returns a summary including any
    unavoidable overflow (total students > total seats). Does not commit.
    """
    caps, default = section_capacities(org_id, class_grade)
    if not caps:
        return {"moved": 0, "overflow": 0, "sections": {}}

    by_sec = {sec: [] for sec in caps}
    for stu in Student.query.filter_by(organization_id=org_id, class_grade=str(class_grade)).all():
        if (stu.status or "").strip().lower() not in ACTIVE_STATUSES:
            continue
        by_sec.setdefault(stu.section, [])
        caps.setdefault(stu.section, default)
        by_sec[stu.section].append(stu)
    for sec in by_sec:
        by_sec[sec].sort(key=_student_name_key)

    moved = 0
    guard = 0
    while guard < 100000:
        guard += 1
        over = [s for s in by_sec if len(by_sec[s]) > caps.get(s, default)]
        if not over:
            break
        src = max(over, key=lambda s: len(by_sec[s]) - caps.get(s, default))
        dest = max(by_sec.keys(), key=lambda s: caps.get(s, default) - len(by_sec[s]))
        if caps.get(dest, default) - len(by_sec[dest]) <= 0:
            break  # every section full -> unavoidable overflow
        stu = by_sec[src].pop()  # alphabetically last leaves first
        stu.section = dest
        stu.class_grade = str(class_grade)
        by_sec[dest].append(stu)
        by_sec[dest].sort(key=_student_name_key)
        moved += 1

    for sec in list(by_sec.keys()):
        resequence_rolls(org_id, class_grade, sec)

    overflow = sum(max(0, len(by_sec[s]) - caps.get(s, default)) for s in by_sec)
    return {"moved": moved, "overflow": overflow,
            "sections": {s: len(by_sec[s]) for s in by_sec}}


def fill_missing_rolls(org_id, class_grade, section):
    """Assign roll numbers ONLY to active students who don't have one yet.

    Used for sections that mix manually-supplied roll numbers with auto ones:
    we never overwrite an organization's provided numbers, we just append the
    next free roll (max + 1) to the unnumbered active students, alphabetically.
    Does not commit.
    """
    students = Student.query.filter_by(
        organization_id=org_id, class_grade=str(class_grade), section=section
    ).all()
    used = [s.roll_no for s in students if s.roll_no is not None]
    nxt = (max(used) + 1) if used else 1
    missing = [
        s for s in students
        if s.roll_no is None and (s.status or "").strip().lower() in ACTIVE_STATUSES
    ]
    missing.sort(key=_student_name_key)
    for s in missing:
        s.roll_no = nxt
        nxt += 1
    return len(missing)


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
