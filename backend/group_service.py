"""Dynamic teaching-group formation.

Turns student stream/elective/language choices into concrete TeachingGroups the
timetable engine can schedule:

  * homeroom group per section (all its students; core subjects)
  * elective groups gathered grade-wide per chosen elective (small same-subject
    groups from different sections naturally merge into one grade group; large
    ones split at max_group_size)
  * language groups for lower grades, same logic

Elective/language groups of a grade share a ``block_key`` so the scheduler can
run them in parallel (a "subject block") — every student attends exactly one and
never clashes. Each group is given a teacher and a room (PE/games -> ground,
specialist subjects -> their room, otherwise a vacant classroom).
"""

import re
from collections import defaultdict

from models import (
    db, Student, Subject, Batch, Teacher, Classroom, SchoolConfig,
    TeachingGroup, GroupMembership,
)
from student_service import ACTIVE_STATUSES
from room_utils import required_room_type


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _cfg(org_id):
    return SchoolConfig.query.filter_by(organization_id=org_id).first()


def _active_students(org_id, grade):
    return [
        s for s in Student.query.filter_by(organization_id=org_id, class_grade=str(grade)).all()
        if (s.status or "").strip().lower() in ACTIVE_STATUSES
    ]


def _all_grades(org_id):
    grades = set()
    for b in Batch.query.filter_by(organization_id=org_id).all():
        if b.grade:
            grades.add(b.grade)
    for (g,) in db.session.query(Student.class_grade).filter_by(organization_id=org_id).distinct():
        if g:
            grades.add(g)
    return grades


def _eligible_teachers(org_id, subject_id, grade):
    out = []
    for t in Teacher.query.filter_by(organization_id=org_id).all():
        if not t.takes_classes:
            continue
        if subject_id in (t.subject_ids or []):
            out.append(t)
            continue
        for sg in (t.subject_grades or []):
            if sg.get("subject_id") == subject_id and str(grade) in [str(x) for x in (sg.get("grades") or [])]:
                out.append(t)
                break
    return out


def _vacant_regular_rooms(org_id):
    """Regular rooms not used as any section's fixed home room — free to host an
    elective group while the rest of the grade is in its own block."""
    home_ids = {b.room_id for b in Batch.query.filter_by(organization_id=org_id).all() if b.room_id}
    return [
        r for r in Classroom.query.filter_by(organization_id=org_id, room_type="regular").all()
        if r.id not in home_ids
    ]


def _room_for_subject(org_id, subject, vacant_pool, vidx):
    """Pick a room for an elective group: special room by subject type (PE/games
    -> ground), otherwise rotate through vacant classrooms."""
    rt = required_room_type(subject.name, bool(getattr(subject, "requires_double", False)))
    if rt:
        room = Classroom.query.filter_by(organization_id=org_id, room_type=rt).first()
        if room:
            return room.id
    if vacant_pool:
        room = vacant_pool[vidx[0] % len(vacant_pool)]
        vidx[0] += 1
        return room.id
    return None


def generate_groups(org_id, options=None):
    """(Re)build auto teaching groups for an organization. Locked groups are kept.

    Returns a summary: counts by type, warnings (below-threshold groups, missing
    teachers), and the created groups. Does not commit.
    """
    cfg = _cfg(org_id)
    min_size = (cfg.min_group_size if cfg and cfg.min_group_size else 10)
    max_size = (cfg.max_group_size if cfg and cfg.max_group_size else 45)
    merge_thr = (cfg.elective_merge_threshold if cfg and cfg.elective_merge_threshold else 10)

    # Wipe previous auto groups, but never touch admin-locked ones.
    locked_ids = [g.id for g in TeachingGroup.query.filter_by(organization_id=org_id, locked=True).all()]
    mq = GroupMembership.query.filter(GroupMembership.organization_id == org_id)
    gq = TeachingGroup.query.filter(TeachingGroup.organization_id == org_id,
                                    TeachingGroup.locked == False)  # noqa: E712
    if locked_ids:
        mq = mq.filter(~GroupMembership.group_id.in_(locked_ids))
    mq.delete(synchronize_session=False)
    gq.delete(synchronize_session=False)
    db.session.flush()

    subjects = Subject.query.filter_by(organization_id=org_id).all()
    subj_by_id = {s.id: s for s in subjects}
    subj_by_norm = {_norm(s.name): s for s in subjects}

    created = []
    warnings = []
    used_teacher = defaultdict(int)
    vacant = _vacant_regular_rooms(org_id)
    vidx = [0]
    counts = {"homeroom": 0, "elective": 0, "language": 0}

    for grade in sorted(_all_grades(org_id)):
        students = _active_students(org_id, grade)
        if not students:
            continue

        # ---- Homeroom group per section -----------------------------------
        by_sec = defaultdict(list)
        for s in students:
            by_sec[s.section].append(s)
        for sec, studs in sorted(by_sec.items()):
            hg = TeachingGroup(
                organization_id=org_id, name=f"{grade}-{sec} Homeroom",
                grade=grade, section=sec, group_type="homeroom", auto_generated=True,
            )
            db.session.add(hg)
            db.session.flush()
            for s in studs:
                db.session.add(GroupMembership(organization_id=org_id, group_id=hg.id, student_id=s.id))
            created.append(hg)
            counts["homeroom"] += 1

        # ---- Elective / language groups (gathered grade-wide) -------------
        chosen = defaultdict(list)  # subject_id -> [students]
        for s in students:
            for name in (s.elective_subjects or []):
                subj = subj_by_norm.get(_norm(name))
                if subj and (subj.subject_type or "core") in ("elective", "language"):
                    chosen[subj.id].append(s)

        for subject_id, studs in sorted(chosen.items()):
            subj = subj_by_id[subject_id]
            is_lang = (subj.subject_type == "language")
            kind = "language" if is_lang else "elective"
            block = f"{grade}|{kind}"

            # Split oversized demand into multiple parallel sub-groups.
            chunks = [studs]
            if len(studs) > max_size:
                chunks = [studs[i:i + max_size] for i in range(0, len(studs), max_size)]

            for ci, chunk in enumerate(chunks):
                suffix = f" ({ci + 1})" if len(chunks) > 1 else ""
                cands = sorted(_eligible_teachers(org_id, subject_id, grade),
                               key=lambda t: used_teacher[t.id])
                tid = cands[0].id if cands else None
                if tid:
                    used_teacher[tid] += 1
                rid = _room_for_subject(org_id, subj, vacant, vidx)

                g = TeachingGroup(
                    organization_id=org_id,
                    name=f"{grade} {subj.name} Group{suffix}",
                    grade=grade, group_type=kind, subject_id=subject_id,
                    teacher_id=tid, room_id=rid,
                    periods_per_week=subj.periods_per_week, block_key=block,
                    auto_generated=True,
                )
                db.session.add(g)
                db.session.flush()
                for s in chunk:
                    db.session.add(GroupMembership(organization_id=org_id, group_id=g.id, student_id=s.id))
                created.append(g)
                counts[kind] += 1

                if len(chunk) < merge_thr:
                    warnings.append(
                        f"{g.name} has only {len(chunk)} students (below threshold {merge_thr}); "
                        f"consider merging or running it small."
                    )
                if not tid:
                    warnings.append(f"No eligible teacher found for {subj.name} (Grade {grade}).")

    db.session.flush()
    return {
        "created": len(created),
        "counts": counts,
        "locked_kept": len(locked_ids),
        "warnings": warnings,
        "groups": [g.to_dict() for g in created],
    }
