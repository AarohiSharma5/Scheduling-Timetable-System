"""Room inventory generation + fixed home-room assignment.

  * ``generate_default_rooms``        -> lay out classrooms across floors + the
                                         standard special rooms + a ground.
  * ``assign_home_rooms_to_batches``  -> give every section a fixed home room,
                                         set its capacity, then redistribute
                                         students so no section exceeds capacity.
"""

import math
from collections import defaultdict

import string

from models import db, Classroom, Batch, SchoolConfig, Student
from student_service import distribute_grade, org_default_capacity, ACTIVE_STATUSES
from period_utils import is_pre_primary


# Default special rooms: (code, name, type, capacity, floor). Mirrors the
# example inventory (dance/ATL/music/art/indoor games/library/labs + ground).
DEFAULT_SPECIAL_ROOMS = [
    ("DANCE", "Dance Room", "dance", 60, 0),
    ("MUSIC", "Music Room", "music", 50, 0),
    ("ART", "Art Room", "art", 50, 1),
    ("ATL", "ATL / Tinkering Lab", "activity", 40, 1),
    ("COMP", "Computer Lab", "activity", 45, 1),
    ("INDOOR", "Indoor Games Room", "indoor_games", 80, 0),
    ("LIB", "Library", "library", 100, 1),
    ("LAB1", "Physics Lab", "lab", 40, 2),
    ("LAB2", "Chemistry Lab", "lab", 40, 2),
    ("LAB3", "Biology Lab", "lab", 40, 2),
    ("HALL", "Auditorium / Hall", "hall", 200, 0),
    ("GROUND", "Ground / Playfield", "ground", 300, None),
]

FLOOR_PREFIX = {0: "G", 1: "1", 2: "2", 3: "3"}


def _grade_key(grade):
    """Order grades: pre-primary first (Nursery→Prep), then numeric, then text."""
    g = str(grade or "").strip()
    pre_order = ["nursery", "lkg", "ukg", "prep", "kg", "pp1", "pp2"]
    low = g.lower().replace(".", "").replace(" ", "")
    if is_pre_primary(g):
        for i, p in enumerate(pre_order):
            if p in low:
                return (0, i, g)
        return (0, 99, g)
    try:
        return (1, int(g), g)
    except ValueError:
        return (2, 0, g)


def _section_label(k):
    """0->A, 25->Z, 26->AA, ... (Excel-style column labels)."""
    out = ""
    while True:
        out = string.ascii_uppercase[k % 26] + out
        k = k // 26 - 1
        if k < 0:
            return out


def _next_section_labels(existing, n):
    labels, k = [], 0
    existing = {str(s).upper() for s in existing}
    while len(labels) < n:
        cand = _section_label(k)
        k += 1
        if cand not in existing:
            labels.append(cand)
            existing.add(cand)
    return labels


def _active_count(org_id, grade):
    return sum(
        1 for s in Student.query.filter_by(organization_id=org_id, class_grade=str(grade)).all()
        if (s.status or "").strip().lower() in ACTIVE_STATUSES
    )


def ensure_sections_for_capacity(org_id, capacity=None):
    """Add sections so every grade has enough seats (ceil(students / capacity)).

    New sections clone subjects + periods/day from an existing sibling section.
    Never deletes a section. Returns the list of created "grade-section" labels.
    Does not commit.
    """
    cap = capacity or org_default_capacity(org_id)
    created = []
    grades = sorted({b.grade for b in Batch.query.filter_by(organization_id=org_id).all()},
                    key=_grade_key)
    for g in grades:
        sibs = Batch.query.filter_by(organization_id=org_id, grade=g).all()
        if not sibs:
            continue
        total = _active_count(org_id, g)
        needed = max(len(sibs), math.ceil(total / cap) if cap else len(sibs))
        if needed <= len(sibs):
            continue
        proto = sibs[0]
        existing = {b.section for b in sibs}
        for lab in _next_section_labels(existing, needed - len(sibs)):
            db.session.add(Batch(
                organization_id=org_id, grade=g, section=lab,
                subject_ids=list(proto.subject_ids or []),
                periods_per_day=proto.periods_per_day,
                student_count=0, capacity=cap,
            ))
            created.append(f"{g}-{lab}")
    db.session.flush()
    return created


def setup_capacity(org_id, options=None):
    """One-shot: ensure enough sections, (re)generate rooms, assign home rooms,
    and redistribute students so no section exceeds capacity. Does not commit."""
    options = dict(options or {})
    created_sections = []
    if options.get("ensure_sections", True):
        created_sections = ensure_sections_for_capacity(org_id, options.get("regular_capacity"))
    options.setdefault("replace", True)
    created_rooms = generate_default_rooms(org_id, options=options)
    result = assign_home_rooms_to_batches(org_id)
    result["created_sections"] = created_sections
    result["created_rooms"] = created_rooms
    return result


def generate_default_rooms(org_id, options=None):
    """Create a default room inventory for an organization. Returns count created.

    options: regular_rooms, regular_capacity, floors, special (list of dicts or
    tuples), replace (bool — wipe existing rooms first).
    """
    options = options or {}

    if options.get("replace"):
        Batch.query.filter_by(organization_id=org_id).update({"room_id": None})
        Classroom.query.filter_by(organization_id=org_id).delete()
        db.session.flush()

    existing = {r.room_id for r in Classroom.query.filter_by(organization_id=org_id).all()}
    default_cap = org_default_capacity(org_id)
    reg_cap = options.get("regular_capacity") or default_cap

    n_batches = Batch.query.filter_by(organization_id=org_id).count()
    # Enough regular rooms to give every section a home room (min 56 for a
    # realistic mid-size school layout).
    regular = int(options.get("regular_rooms") or max(56, n_batches))
    floors = int(options.get("floors") or 4)
    per_floor = max(1, math.ceil(regular / floors))

    created = 0
    seq_by_floor = defaultdict(int)
    for i in range(regular):
        floor = min(i // per_floor, floors - 1)
        seq_by_floor[floor] += 1
        prefix = FLOOR_PREFIX.get(floor, str(floor))
        code = f"{prefix}{seq_by_floor[floor]:02d}"
        if code in existing:
            continue
        db.session.add(Classroom(
            organization_id=org_id, room_id=code, room_name=f"Classroom {code}",
            capacity=reg_cap, room_type="regular", floor=floor,
        ))
        existing.add(code)
        created += 1

    specials = options.get("special") or DEFAULT_SPECIAL_ROOMS
    for spec in specials:
        if isinstance(spec, dict):
            code = spec.get("room_id"); name = spec.get("room_name")
            rtype = spec.get("room_type", "activity"); cap = spec.get("capacity") or default_cap
            floor = spec.get("floor")
        else:
            code, name, rtype, cap, floor = spec
        if not code or code in existing:
            continue
        db.session.add(Classroom(
            organization_id=org_id, room_id=code, room_name=name,
            capacity=cap, room_type=rtype, floor=floor,
        ))
        existing.add(code)
        created += 1

    return created


def assign_home_rooms_to_batches(org_id):
    """Assign a fixed regular home room to every section, set capacities, and
    redistribute students. Returns a summary dict. Does not commit."""
    regular = (
        Classroom.query.filter_by(organization_id=org_id, room_type="regular")
        .order_by(Classroom.floor.asc().nullsfirst(), Classroom.room_id.asc())
        .all()
    )
    batches = Batch.query.filter_by(organization_id=org_id).all()
    batches.sort(key=lambda b: (_grade_key(b.grade), str(b.section)))

    assigned = 0
    unassigned = []
    for i, b in enumerate(batches):
        if i < len(regular):
            room = regular[i]
            b.room_id = room.id
            b.capacity = room.capacity
            room.assigned_class = f"{b.grade}-{b.section}"
            assigned += 1
        else:
            unassigned.append(f"{b.grade}-{b.section}")

    db.session.flush()

    distribution = {}
    for grade in sorted({b.grade for b in batches}, key=_grade_key):
        distribution[grade] = distribute_grade(org_id, grade)

    return {
        "assigned": assigned,
        "unassigned": unassigned,
        "regular_rooms": len(regular),
        "distribution": distribution,
    }
