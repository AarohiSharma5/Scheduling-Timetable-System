"""Shared period-layout math.

The scheduler and the PDF exporter both need to agree on the *shape* of a school
day: how many periods fit between start and end time, which period is lunch, and
how short a junior grade's day should be. Keeping that logic here guarantees the
generated timetable and the exported PDF never disagree.
"""

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Grade labels treated as pre-primary, where a single homeroom teacher can take
# most subjects. Matching is done on a normalized (lower, no-punctuation) form so
# "L.K.G", "lkg", "Pre Primary" and "pre-primary" all map correctly.
PRE_PRIMARY_GRADES = {
    "nursery", "prenursery", "playgroup", "play group", "pg",
    "lkg", "ukg", "kg", "kg1", "kg2", "kindergarten",
    "prep", "preparatory", "preprimary", "pre primary",
    "pp", "pp1", "pp2", "preschool",
}

# Subjects that always go to a specialist even in single-teacher mode.
DEFAULT_SUPPORT_SUBJECTS = ["Art", "Music", "Dance", "PE", "Physical Education", "Games", "Sports"]


def _norm_grade(grade):
    """Normalize a grade label for pre-primary matching."""
    s = str(grade or "").strip().lower()
    return "".join(ch for ch in s if ch.isalnum() or ch == " ").strip()


def is_pre_primary(grade):
    """True when a grade label denotes a pre-primary class (Nursery/LKG/UKG/Prep)."""
    n = _norm_grade(grade)
    if not n:
        return False
    if n in PRE_PRIMARY_GRADES:
        return True
    compact = n.replace(" ", "")
    return compact in PRE_PRIMARY_GRADES


def _to_min(hhmm, default=0):
    """Parse 'HH:MM' to minutes-since-midnight; fall back to `default`."""
    try:
        parts = str(hhmm).split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError, AttributeError, TypeError):
        return default


def _fmt(mins):
    mins = max(0, int(mins))
    return f"{(mins // 60) % 24:02d}:{mins % 60:02d}"


def school_periods_per_day(config):
    """Number of period slots that fill start_time..end_time at period_duration.

    This is the single source of truth: a school open 08:00–14:00 with 45-minute
    periods has exactly 8 slots, regardless of any stale stored value.
    """
    dur = config.period_duration or 45
    start = _to_min(config.start_time, 8 * 60)
    end = _to_min(config.end_time, 15 * 60)
    n = (end - start) // dur
    return max(1, n)


def has_lunch(config):
    return bool(getattr(config, "has_lunch_break", True))


def has_short_break(config):
    return bool(getattr(config, "has_short_break", False))


def lunch_period_index(config, n=None):
    """1-based index of the period reserved for lunch, or None.

    None when lunch is disabled or lunch time falls outside the school day.
    """
    if not has_lunch(config):
        return None
    if n is None:
        n = school_periods_per_day(config)
    dur = config.period_duration or 45
    start = _to_min(config.start_time, 8 * 60)
    lunch_start = _to_min(config.lunch_start, 12 * 60)
    idx = ((lunch_start - start) // dur) + 1
    if idx < 1 or idx > n:
        return None
    return idx


def short_break_period_index(config, n=None):
    """1-based index of the period reserved for the short (fruit) break, or None.

    Mirrors lunch: derived from the break's start time. Returns None when the
    break is disabled, falls outside the day, or would collide with lunch.
    """
    if not has_short_break(config):
        return None
    if n is None:
        n = school_periods_per_day(config)
    dur = config.period_duration or 45
    start = _to_min(config.start_time, 8 * 60)
    sb_start = _to_min(getattr(config, "short_break_start", None), -1)
    if sb_start < 0:
        return None
    idx = ((sb_start - start) // dur) + 1
    if idx < 1 or idx > n:
        return None
    if idx == lunch_period_index(config, n):
        return None  # never overlap lunch
    return idx


def build_layout(config, count=None):
    """Return per-day period rows: {number, start, end, is_lunch}.

    `count` caps the number of periods (used to give junior grades a shorter day).
    Lunch is always computed against the *full* school day so its clock time is
    stable across grades.
    """
    full_n = school_periods_per_day(config)
    n = full_n if count is None else min(full_n, max(1, count))
    dur = config.period_duration or 45
    start = _to_min(config.start_time, 8 * 60)
    lunch_idx = lunch_period_index(config, full_n)
    short_idx = short_break_period_index(config, full_n)

    rows = []
    # Optional zero period (period 0) shown before the regular day.
    if getattr(config, "zero_period_enabled", False):
        zs = _to_min(getattr(config, "zero_period_start", None), max(0, start - 30))
        zd = getattr(config, "zero_period_duration", None) or 30
        rows.append({
            "number": 0,
            "start": _fmt(zs),
            "end": _fmt(zs + zd),
            "is_lunch": False,
            "is_zero": True,
        })
    for i in range(1, n + 1):
        s = start + (i - 1) * dur
        rows.append({
            "number": i,
            "start": _fmt(s),
            "end": _fmt(s + dur),
            "is_lunch": (i == lunch_idx),
            "is_short_break": (i == short_idx),
        })
    return rows


def working_days(config):
    w = config.working_days or 5
    return WEEK_DAYS[:max(1, min(w, len(WEEK_DAYS)))]


def batch_period_count(batch, config):
    """Effective number of periods for a class (its own override, capped to school)."""
    school_n = school_periods_per_day(config)
    bp = getattr(batch, "periods_per_day", None)
    if bp and bp > 0:
        return min(bp, school_n)
    return school_n
