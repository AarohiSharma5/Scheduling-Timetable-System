"""Shared room/facility helpers.

Defines the canonical room types and the rule that maps a subject to the
*special* room its periods must happen in (art room, music room, ground, lab,
…). Subjects with no special room are taught in the section's fixed home
classroom, with teachers rotating in.
"""

# Canonical room types. "regular" = a normal home classroom; the rest are the
# shared special rooms students travel to for co-curricular / lab periods.
REGULAR_TYPE = "regular"
GROUND_TYPE = "ground"
SPECIAL_TYPES = ["lab", "library", "art", "music", "dance", "indoor_games", "ground", "hall", "activity"]
ALL_ROOM_TYPES = [REGULAR_TYPE] + SPECIAL_TYPES

ROOM_TYPE_LABELS = {
    "regular": "Regular classroom",
    "lab": "Laboratory",
    "library": "Library",
    "art": "Art room",
    "music": "Music room",
    "dance": "Dance room",
    "indoor_games": "Indoor games",
    "ground": "Ground / playfield",
    "hall": "Hall / auditorium",
    "activity": "Activity room (ATL etc.)",
}

# Subject-name keyword -> required special room type. First match wins. Anything
# that doesn't match is taught in the home classroom (room type None).
_SUBJECT_KEYWORDS = [
    (("physical education", "p.e", " pe", "pe ", "games", "sport", "athletic"), "ground"),
    (("dance", "dancing"), "dance"),
    (("music", "singing", "instrument", "vocal"), "music"),
    (("art", "drawing", "painting", "craft", "sketch"), "art"),
    (("library", "reading", "book club"), "library"),
    (("computer", "informatics", "coding", "robotics", "atl", "tinkering"), "activity"),
    (("physics lab", "chemistry lab", "biology lab", "science lab", "laboratory", " lab"), "lab"),
]


def required_room_type(subject_name, requires_double=False):
    """The special room type a subject needs, or None for a home-classroom subject.

    `requires_double` (lab/double subjects) nudges generic science subjects into
    a lab even when the name doesn't literally contain "lab".
    """
    name = f" {str(subject_name or '').strip().lower()} "
    for keywords, room_type in _SUBJECT_KEYWORDS:
        if any(k in name for k in keywords):
            return room_type
    if requires_double and any(s in name for s in ("science", "physics", "chemistry", "biology")):
        return "lab"
    return None
