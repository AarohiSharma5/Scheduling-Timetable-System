"""Pre-flight feasibility planning for timetable generation.

Three jobs, shared by the audit endpoint AND the scheduling engine so what the
admin sees before generating is exactly what the engine will do:

1. ``build_eligibility``     — who can teach which (subject, section) block.
2. ``plan_block_assignments`` — give every (section, subject) block to ONE
   teacher (whole-section ownership, like real schools), balanced against each
   teacher's weekly capacity instead of greedily overloading one person.
3. ``audit`` / ``suggest_charge_moves`` / ``apply_charge_moves`` — explain any
   capacity gap and fix it by moving non-teaching charges from overloaded
   subject teachers to colleagues with lighter loads. Class-teacher duty is
   never moved (class teachership is preserved).
"""

from collections import defaultdict

from models import (
    db, Teacher, Batch, Subject, SchoolConfig, ClassSubjectConfig, AuditLog,
)
import period_utils

# A charge with this name is the class-teachership reservation: it stays with
# the class teacher no matter what.
PROTECTED_CHARGE_NAMES = {"class teacher", "class teachership", "ct"}

DEFAULT_TEACHER_MAX = 24


# ---------------------------------------------------------------------------
# Context loading
# ---------------------------------------------------------------------------

def load_context(org_id):
    """Load everything the planner/audit needs for one organization."""
    config = SchoolConfig.query.filter_by(organization_id=org_id).first()
    teachers = Teacher.query.filter_by(organization_id=org_id).all()
    batches = Batch.query.filter_by(organization_id=org_id).all()
    subjects = Subject.query.filter_by(organization_id=org_id).all()
    cls_cfg = {(str(c.grade), c.subject_id): c
               for c in ClassSubjectConfig.query.filter_by(organization_id=org_id).all()}
    return {
        "org_id": org_id,
        "config": config,
        "teachers": teachers,
        "batches": batches,
        "subjects": subjects,
        "cls_cfg": cls_cfg,
        "subject_by_id": {s.id: s for s in subjects},
        "batch_by_id": {b.id: b for b in batches},
        "teacher_by_id": {t.id: t for t in teachers},
    }


def eff_periods(ctx, batch, subject_id):
    """Weekly periods this class needs of a subject (per-class override aware)."""
    c = ctx["cls_cfg"].get((str(batch.grade), subject_id))
    if c and c.periods_per_week:
        return c.periods_per_week
    s = ctx["subject_by_id"].get(subject_id)
    return (s.periods_per_week or 0) if s else 0


def eff_max_per_day(ctx, batch, subject_id):
    c = ctx["cls_cfg"].get((str(batch.grade), subject_id))
    if c and c.max_per_day:
        return c.max_per_day
    s = ctx["subject_by_id"].get(subject_id)
    return (getattr(s, "max_periods_per_day", None) or 1) if s else 1


def teacher_capacity(teacher):
    """Weekly teaching periods available (already net of charges + CT hours)."""
    if not teacher.takes_classes:
        return 0
    return max(0, teacher.max_periods_per_week or DEFAULT_TEACHER_MAX)


def weekly_slot_ceiling(config):
    """Max periods a teacher can realistically be timetabled per week.

    The grid only has (periods/day - breaks) x days cells; planning anyone at
    100% of that guarantees clashes (zero slack to dodge other constraints), so
    a small buffer is always reserved.
    """
    if config is None:
        return None
    per_day = period_utils.school_periods_per_day(config)
    if period_utils.has_lunch(config) and period_utils.lunch_period_index(config):
        per_day -= 1
    sb = period_utils.short_break_period_index(config)
    if period_utils.has_short_break(config) and sb:
        per_day -= 1
    weekly = max(1, per_day) * len(period_utils.working_days(config))
    slack = max(2, round(weekly * 0.08))
    return max(1, weekly - slack)


def build_eligibility(teachers, batches):
    """teacher_id -> set of (subject_id, batch_id) pairs the teacher can take.

    Structured teaching_assignments are authoritative; grade-level capability
    (subject_grades) widens the pool so the planner can re-balance sections of
    the same grade across teachers. Falls back to the flat lists for old data.
    """
    batches_by_grade = defaultdict(list)
    for b in batches:
        batches_by_grade[str(b.grade)].append(b)

    eligibility = {}
    for t in teachers:
        pairs = set()
        assignments = getattr(t, "teaching_assignments", None) or []
        if assignments:
            for a in assignments:
                sid = a.get("subject_id")
                for bid in (a.get("batch_ids") or []):
                    pairs.add((sid, bid))
        else:
            for sid in (t.subject_ids or []):
                for bid in (t.assigned_batch_ids or []):
                    pairs.add((sid, bid))
        # Grade-level capability: can teach the subject to ANY section of the grade.
        for cap in (getattr(t, "subject_grades", None) or []):
            sid = cap.get("subject_id")
            for g in (cap.get("grades") or []):
                for b in batches_by_grade.get(str(g), []):
                    pairs.add((sid, b.id))
        eligibility[t.id] = pairs
    return eligibility


def _homeroom_batches(ctx):
    """batch_id -> homeroom teacher id for pre-primary single-teacher classes."""
    config = ctx["config"]
    mode = (getattr(config, "pre_primary_mode", "single") or "single").lower()
    if mode != "single":
        return {}
    class_teacher_of = {}
    for t in ctx["teachers"]:
        if getattr(t, "class_teacher_batch_id", None):
            class_teacher_of.setdefault(t.class_teacher_batch_id, t.id)
    out = {}
    for b in ctx["batches"]:
        if not period_utils.is_pre_primary(b.grade):
            continue
        hr = getattr(b, "homeroom_teacher_id", None) or class_teacher_of.get(b.id)
        if hr:
            out[b.id] = hr
    return out


def _support_subject_ids(ctx):
    config = ctx["config"]
    support = (getattr(config, "pre_primary_support_subjects", None)
               or period_utils.DEFAULT_SUPPORT_SUBJECTS)
    names = {str(n).strip().lower() for n in support if str(n).strip()}
    return {s.id for s in ctx["subjects"] if (s.name or "").strip().lower() in names}


# ---------------------------------------------------------------------------
# Whole-section block planner
# ---------------------------------------------------------------------------

def plan_block_assignments(ctx, eligibility=None, prefs=None, rng=None):
    """Assign each (batch, subject) block wholly to one teacher, capacity-aware.

    Returns {
      "owner":      {(batch_id, subject_id): teacher_id},
      "planned":    {teacher_id: planned weekly periods},
      "capacity":   {teacher_id: weekly capacity},
      "shortfalls": [ {batch_id, subject_id, periods, deficit, eligible_teacher_ids} ],
      "unstaffed":  [ {batch_id, subject_id, periods} ],   # nobody can teach it
    }

    Blocks are processed most-constrained-first (fewest eligible teachers, then
    biggest weekly load) and each block goes to the eligible teacher with the
    most remaining capacity — preferring a teacher who already owns another
    block in the same section (subject-cohesion) and the section's class
    teacher for their own class. A block is never split between teachers.
    """
    teachers = ctx["teachers"]
    if eligibility is None:
        eligibility = build_eligibility(teachers, ctx["batches"])
    prefs = prefs or {}

    def _pref_rank(tid, bid, sid):
        p = prefs.get(tid)
        if not p:
            return 0
        rank = 0
        if bid in (getattr(p, "preferred_classes", None) or []):
            rank += 2
        if sid in (getattr(p, "preferred_subjects", None) or []):
            rank += 1
        return rank

    homeroom_of = _homeroom_batches(ctx)
    support_ids = _support_subject_ids(ctx)

    class_teacher_of = {}
    for t in teachers:
        if getattr(t, "class_teacher_batch_id", None):
            class_teacher_of.setdefault(t.class_teacher_batch_id, t.id)

    # Per-batch day length. Junior grades run fewer periods, so all their
    # teaching squeezes into the early-period "window" — a teacher's junior
    # load must fit those windows, not just their gross weekly max.
    config = ctx.get("config")
    batch_limit = {}
    if config is not None:
        for b in ctx["batches"]:
            batch_limit[b.id] = period_utils.batch_period_count(b, config)

    def _usable_within(limit):
        """Weekly schedulable cells with period number <= limit."""
        per_day = limit
        if period_utils.has_lunch(config):
            li = period_utils.lunch_period_index(config)
            if li and li <= limit:
                per_day -= 1
        if period_utils.has_short_break(config):
            si = period_utils.short_break_period_index(config)
            if si and si <= limit:
                per_day -= 1
        return max(0, per_day) * len(period_utils.working_days(config))

    tiers = sorted(set(batch_limit.values())) if batch_limit else []
    window_allowed = {}
    for L in tiers:
        u = _usable_within(L)
        # 12% slack: short junior windows get congested fast, so a teacher is
        # never planned to within a couple periods of a window's full size.
        window_allowed[L] = max(0, u - max(2, round(u * 0.12)))

    # teacher_id -> {day-length tier -> planned periods in batches of that tier}
    window_load = defaultdict(lambda: defaultdict(int))

    def _window_overflow(tid, limit, w):
        """How far adding w periods in a `limit`-length batch overshoots any window."""
        if not tiers or limit is None:
            return 0
        worst = 0
        for W in tiers:
            if W < limit:
                continue
            cum = sum(v for L2, v in window_load[tid].items() if L2 <= W) + w
            worst = max(worst, cum - window_allowed[W])
        return max(0, worst)

    # Collect the blocks the planner must staff. Homeroom-covered ones go to
    # the engine's pre-primary path, but they still consume the homeroom
    # teacher's REAL weekly slots (in their batch's short window).
    blocks = []
    homeroom_load = defaultdict(int)
    for b in ctx["batches"]:
        hr = homeroom_of.get(b.id)
        for sid in (b.subject_ids or []):
            w = eff_periods(ctx, b, sid)
            if w <= 0:
                continue
            if hr and sid not in support_ids:
                homeroom_load[hr] += w
                window_load[hr][batch_limit.get(b.id) or 0] += w
                continue  # taken by the homeroom teacher
            blocks.append({"batch_id": b.id, "subject_id": sid, "periods": w})

    # Plannable capacity: the teacher's weekly max, capped by how many grid
    # cells a week actually has (minus slack), minus their homeroom commitment.
    ceiling = weekly_slot_ceiling(config)
    capacity = {}
    for t in teachers:
        cap = teacher_capacity(t)
        if ceiling is not None:
            cap = min(cap, ceiling)
        capacity[t.id] = max(0, cap - homeroom_load.get(t.id, 0))
    remaining = dict(capacity)
    planned = {t.id: 0 for t in teachers}
    blocks_owned = defaultdict(int)        # teacher_id -> blocks taken so far
    sections_of_teacher = defaultdict(set)  # teacher_id -> batch_ids owned

    for blk in blocks:
        blk["elig"] = [t.id for t in teachers
                       if (blk["subject_id"], blk["batch_id"]) in eligibility.get(t.id, ())
                       and capacity.get(t.id, 0) > 0]

    # Optional restart diversity: shuffle first so equally-ranked blocks and
    # equally-ranked teachers tie-break differently on each generation attempt.
    if rng is not None:
        rng.shuffle(blocks)
        for blk in blocks:
            rng.shuffle(blk["elig"])

    # Most constrained first: fewest eligible teachers, then largest block.
    # (sort is stable, so the shuffle above only affects ties)
    blocks.sort(key=lambda blk: (len(blk["elig"]), -blk["periods"]))

    owner = {}
    shortfalls = []
    unstaffed = []

    for blk in blocks:
        w, bid, sid = blk["periods"], blk["batch_id"], blk["subject_id"]
        if not blk["elig"]:
            unstaffed.append({"batch_id": bid, "subject_id": sid, "periods": w})
            continue
        limit = batch_limit.get(bid)

        def rank(tid):
            fits = (remaining.get(tid, 0) >= w
                    and _window_overflow(tid, limit, w) == 0)
            return (
                fits,                                       # can take the whole block
                tid == class_teacher_of.get(bid),           # own section first
                bid in sections_of_teacher[tid],            # already teaches this section
                _pref_rank(tid, bid, sid),                  # soft teacher preference
                remaining.get(tid, 0),                      # then most spare capacity
                -blocks_owned[tid],                         # spread block count
            )

        best = max(blk["elig"], key=rank)
        owner[(bid, sid)] = best
        deficit = max(0, w - remaining.get(best, 0))
        deficit = max(deficit, _window_overflow(best, limit, w))
        if deficit > 0:
            shortfalls.append({
                "batch_id": bid, "subject_id": sid, "periods": w,
                "deficit": deficit, "teacher_id": best,
                "eligible_teacher_ids": blk["elig"],
            })
        remaining[best] = remaining.get(best, 0) - w  # may go negative: tracked as deficit
        planned[best] = planned.get(best, 0) + w
        window_load[best][limit or 0] += w
        blocks_owned[best] += 1
        sections_of_teacher[best].add(bid)

    return {
        "owner": owner,
        "planned": planned,
        "capacity": capacity,
        "remaining": remaining,
        "shortfalls": shortfalls,
        "unstaffed": unstaffed,
        # All eligible teachers per block, so the engine's repair pass can
        # reassign a whole block to a colleague when the owner can't fit it.
        "eligible": {(blk["batch_id"], blk["subject_id"]): list(blk["elig"])
                     for blk in blocks},
    }


# ---------------------------------------------------------------------------
# Charge rebalancing
# ---------------------------------------------------------------------------

def _movable_charges(teacher):
    """Charge entries that can be handed to a colleague (never class-teachership)."""
    out = []
    for c in (teacher.charges or []):
        name = str(c.get("name") or "").strip()
        hours = int(c.get("hours_per_week") or 0)
        if hours <= 0 or name.lower() in PROTECTED_CHARGE_NAMES:
            continue
        out.append({"name": name, "hours": hours, "charge_id": c.get("charge_id")})
    return out


def suggest_charge_moves(ctx, plan):
    """Moves of non-teaching charges that would close the planned deficits.

    For every overloaded teacher (planned > capacity) holding movable charges,
    propose handing a charge to the teacher with the most spare capacity left
    after the plan. One move never overloads the receiver.
    """
    teacher_by_id = ctx["teacher_by_id"]
    subject_name = {s.id: s.name for s in ctx["subjects"]}

    overload = {}
    for tid, p in plan["planned"].items():
        over = p - plan["capacity"].get(tid, 0)
        if over > 0:
            overload[tid] = over

    # Subjects each overloaded teacher is short on (for the explanation line).
    short_subjects = defaultdict(set)
    for sf in plan["shortfalls"]:
        short_subjects[sf["teacher_id"]].add(subject_name.get(sf["subject_id"], "?"))

    # Spare capacity per potential receiver, consumed as we assign moves.
    spare = {tid: max(0, plan["capacity"].get(tid, 0) - plan["planned"].get(tid, 0))
             for tid in plan["capacity"]}

    moves = []
    for tid, over in sorted(overload.items(), key=lambda kv: -kv[1]):
        giver = teacher_by_id.get(tid)
        if not giver:
            continue
        need = over
        for charge in sorted(_movable_charges(giver), key=lambda c: -c["hours"]):
            if need <= 0:
                break
            receivers = [rid for rid, sp in spare.items()
                         if rid != tid and sp >= charge["hours"]
                         and teacher_by_id.get(rid) is not None]
            if not receivers:
                continue
            rid = max(receivers, key=lambda r: spare[r])
            receiver = teacher_by_id[rid]
            moves.append({
                "from_teacher_id": tid,
                "from_name": giver.name,
                "to_teacher_id": rid,
                "to_name": receiver.name,
                "charge_name": charge["name"],
                "charge_id": charge.get("charge_id"),
                "hours": charge["hours"],
                "reason": (
                    f"Frees {charge['hours']} period(s)/week for "
                    f"{', '.join(sorted(short_subjects.get(tid, set())) or ['core subjects'])}"
                ),
            })
            spare[rid] -= charge["hours"]
            need -= charge["hours"]
    return moves


def apply_charge_moves(org_id, moves, actor_user_id=None):
    """Hand the given charges over and adjust both teachers' weekly caps."""
    applied = []
    errors = []
    for m in moves:
        giver = Teacher.query.filter_by(id=m.get("from_teacher_id"), organization_id=org_id).first()
        receiver = Teacher.query.filter_by(id=m.get("to_teacher_id"), organization_id=org_id).first()
        if not giver or not receiver:
            errors.append(f"Move skipped: unknown teacher in {m}")
            continue
        name = str(m.get("charge_name") or "").strip()
        if name.lower() in PROTECTED_CHARGE_NAMES:
            errors.append(f"Move skipped: '{name}' (class-teachership) is never moved")
            continue

        charges = list(giver.charges or [])
        idx = next((i for i, c in enumerate(charges)
                    if str(c.get("name") or "").strip() == name
                    and int(c.get("hours_per_week") or 0) == int(m.get("hours") or 0)), None)
        if idx is None:
            errors.append(f"Move skipped: {giver.name} no longer holds '{name}'")
            continue

        entry = charges.pop(idx)
        hours = int(entry.get("hours_per_week") or 0)
        giver.charges = charges
        receiver.charges = list(receiver.charges or []) + [entry]
        giver.max_periods_per_week = (giver.max_periods_per_week or DEFAULT_TEACHER_MAX) + hours
        receiver.max_periods_per_week = max(
            0, (receiver.max_periods_per_week or DEFAULT_TEACHER_MAX) - hours)
        applied.append({
            "charge": name, "hours": hours,
            "from": giver.name, "to": receiver.name,
        })

    if applied:
        db.session.add(AuditLog(
            organization_id=org_id,
            user_id=actor_user_id,
            action="charges.rebalance",
            detail={"moves": applied},
        ))
        db.session.commit()
    return applied, errors


# ---------------------------------------------------------------------------
# Full audit
# ---------------------------------------------------------------------------

def _weekly_slot_budget(ctx, batch):
    """Schedulable periods/week for this class (day length minus breaks/assembly)."""
    config = ctx["config"]
    days = period_utils.working_days(config)
    day_len = period_utils.batch_period_count(batch, config)
    per_day = day_len
    lunch_idx = period_utils.lunch_period_index(config)
    if period_utils.has_lunch(config) and lunch_idx and lunch_idx <= day_len:
        per_day -= 1
    sb_idx = period_utils.short_break_period_index(config)
    if period_utils.has_short_break(config) and sb_idx and sb_idx <= day_len:
        per_day -= 1
    budget = per_day * len(days)

    # Assembly slots consume class periods too.
    mode = (getattr(config, "assembly_mode", "disabled") or "disabled").lower()
    a_period = int(getattr(config, "assembly_period", 1) or 1)
    if mode != "disabled" and a_period <= day_len:
        if mode == "daily":
            budget -= len(days)
        elif mode == "grade_wise":
            want = {str(g) for g in (getattr(config, "assembly_grades", None) or [])}
            if str(batch.grade) in want:
                budget -= len(days)
        elif mode == "day_wise":
            sched = getattr(config, "assembly_schedule", None) or {}
            budget -= sum(1 for d in days if str(batch.grade) in {str(g) for g in (sched.get(d) or [])})
    return max(0, budget)


def _room_capacity_report(ctx):
    """Weekly demand vs supply for each shared special room type.

    Only room types the org actually has are constrained (a subject with no
    matching special room is taught in the home classroom). Pre-primary
    classes always stay in their home room, so they add no special-room demand.
    """
    from models import Classroom
    from room_utils import required_room_type

    config = ctx["config"]
    rooms = Classroom.query.filter_by(organization_id=ctx["org_id"]).all()
    if not rooms:
        return []

    pool = defaultdict(int)
    for r in rooms:
        if r.room_type not in ("regular", None):
            pool[r.room_type] += 1

    days = len(period_utils.working_days(config))
    per_day = period_utils.school_periods_per_day(config)
    if period_utils.has_lunch(config) and period_utils.lunch_period_index(config):
        per_day -= 1
    sb = period_utils.short_break_period_index(config)
    if period_utils.has_short_break(config) and sb:
        per_day -= 1
    weekly_slots = max(0, per_day) * days

    ground_limit = getattr(config, "ground_max_concurrent_batches", 4) or 4

    demand = defaultdict(int)
    for b in ctx["batches"]:
        if period_utils.is_pre_primary(b.grade):
            continue
        for sid in (b.subject_ids or []):
            s = ctx["subject_by_id"].get(sid)
            if not s:
                continue
            rt = required_room_type(s.name, bool(getattr(s, "requires_double", False)))
            if rt and pool.get(rt):
                w = eff_periods(ctx, b, sid)
                if rt == "lab":
                    # Only the practical double block uses the lab; theory
                    # periods are taught in the home classroom.
                    w = 2 if w >= 2 else 0
                demand[rt] += w

    out = []
    for rt, need in sorted(demand.items(), key=lambda kv: -kv[1]):
        n_rooms = pool.get(rt, 0)
        supply = weekly_slots * (ground_limit if rt == "ground" else n_rooms)
        out.append({
            "room_type": rt,
            "rooms": n_rooms,
            "demand": need,
            "supply": supply,
            "status": "over" if need > supply else "ok",
        })
    return out


def audit(org_id):
    """Full pre-flight report: class budgets, teacher supply, suggested fixes."""
    ctx = load_context(org_id)
    if not ctx["config"]:
        return {"ok": False, "error": "School configuration not found"}
    if not ctx["batches"] or not ctx["subjects"] or not ctx["teachers"]:
        return {"ok": False, "error": "Add classes, subjects and teachers first"}

    config = ctx["config"]
    days = len(period_utils.working_days(config))
    subject_name = {s.id: s.name for s in ctx["subjects"]}

    # ---- 1) Per-class period budget vs subject demand ----------------------
    classes = []
    for b in ctx["batches"]:
        budget = _weekly_slot_budget(ctx, b)
        rows = []
        demand = 0
        impossible = []
        for sid in (b.subject_ids or []):
            w = eff_periods(ctx, b, sid)
            if w <= 0:
                continue
            demand += w
            rows.append({"subject_id": sid, "subject": subject_name.get(sid, "?"), "periods": w})
            # Spacing feasibility: w periods can't fit in `days` if capped per day.
            max_day = eff_max_per_day(ctx, b, sid)
            if w > days * max_day:
                impossible.append(
                    f"{subject_name.get(sid, '?')}: {w}/week can never fit "
                    f"({days} days × max {max_day}/day)"
                )
        status = "over" if demand > budget else ("tight" if demand == budget else "ok")
        classes.append({
            "batch_id": b.id,
            "label": f"Grade {b.grade}-{b.section}",
            "budget": budget,
            "demand": demand,
            "free": budget - demand,
            "status": status,
            "subjects": sorted(rows, key=lambda r: -r["periods"]),
            "impossible": impossible,
        })

    # ---- 2) Teacher supply via the real block plan --------------------------
    plan = plan_block_assignments(ctx)

    deficit_by_subject = defaultdict(int)
    for sf in plan["shortfalls"]:
        deficit_by_subject[sf["subject_id"]] += sf["deficit"]
    unstaffed_by_subject = defaultdict(list)
    for u in plan["unstaffed"]:
        b = ctx["batch_by_id"].get(u["batch_id"])
        unstaffed_by_subject[u["subject_id"]].append(
            f"Grade {b.grade}-{b.section}" if b else f"Batch {u['batch_id']}")

    demand_by_subject = defaultdict(int)
    sections_by_subject = defaultdict(int)
    for b in ctx["batches"]:
        for sid in (b.subject_ids or []):
            w = eff_periods(ctx, b, sid)
            if w > 0:
                demand_by_subject[sid] += w
                sections_by_subject[sid] += 1

    eligibility = build_eligibility(ctx["teachers"], ctx["batches"])
    subjects_report = []
    for sid, demand in sorted(demand_by_subject.items(), key=lambda kv: -kv[1]):
        pool = [t for t in ctx["teachers"]
                if any(p[0] == sid for p in eligibility.get(t.id, ())) and teacher_capacity(t) > 0]
        deficit = deficit_by_subject.get(sid, 0)
        missing_sections = unstaffed_by_subject.get(sid, [])
        subjects_report.append({
            "subject_id": sid,
            "subject": subject_name.get(sid, "?"),
            "demand": demand,
            "sections": sections_by_subject[sid],
            "teachers": len(pool),
            "deficit": deficit,
            "unstaffed_sections": missing_sections,
            "status": ("unstaffed" if missing_sections
                       else "short" if deficit > 0 else "ok"),
        })

    # ---- 3) Teacher loads + suggested charge moves --------------------------
    teacher_loads = []
    for t in ctx["teachers"]:
        cap = plan["capacity"].get(t.id, 0)
        p = plan["planned"].get(t.id, 0)
        if cap <= 0 and p <= 0:
            continue
        teacher_loads.append({
            "teacher_id": t.id,
            "name": t.name,
            "planned": p,
            "capacity": cap,
            "charge_hours": t.charge_hours,
            "is_class_teacher": bool(t.is_class_teacher),
            "status": "over" if p > cap else ("full" if p == cap else "ok"),
        })
    teacher_loads.sort(key=lambda r: (r["capacity"] - r["planned"]))

    moves = suggest_charge_moves(ctx, plan)
    freed = sum(m["hours"] for m in moves)
    total_deficit = sum(deficit_by_subject.values())

    rooms_report = _room_capacity_report(ctx)

    problems = (
        [c for c in classes if c["status"] == "over" or c["impossible"]]
        or [s for s in subjects_report if s["status"] != "ok"]
        or [r for r in rooms_report if r["status"] == "over"]
    )

    return {
        "ok": not problems,
        "summary": {
            "classes_total": len(classes),
            "classes_over_budget": sum(1 for c in classes if c["status"] == "over"),
            "subjects_short": sum(1 for s in subjects_report if s["status"] == "short"),
            "subjects_unstaffed": sum(1 for s in subjects_report if s["status"] == "unstaffed"),
            "teachers_overloaded": sum(1 for t in teacher_loads if t["status"] == "over"),
            "rooms_over_capacity": sum(1 for r in rooms_report if r["status"] == "over"),
            "total_capacity_deficit": total_deficit,
            "rebalance_can_free": freed,
            "rebalance_covers_deficit": freed >= total_deficit and total_deficit > 0,
        },
        "classes": classes,
        "subjects": subjects_report,
        "teacher_loads": teacher_loads[:80],
        "rooms": rooms_report,
        "rebalance_suggestions": moves,
    }
