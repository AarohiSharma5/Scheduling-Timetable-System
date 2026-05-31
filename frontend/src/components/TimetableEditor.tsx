import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";

interface PeriodRow { number: number; start: string; end: string; is_lunch: boolean; }
interface BatchInfo { id: number; grade: string; section: string; display_name?: string; periods_per_day?: number | null; subject_ids?: number[]; }
interface SubjectInfo { id: number; name: string; }
interface TeacherInfo { id: number; name: string; teacher_code?: string | null; subject_ids?: number[]; assigned_batch_ids?: number[]; unavailable_slots?: { day: string; period: number }[]; }

interface Cell { subject_id: number | null; teacher_id: number | null; room: string | null; is_lunch: boolean; is_pinned: boolean; }
type Grid = Record<string, Cell>;

interface Conflict { type: string; severity: "hard" | "soft"; message: string; day?: string; period?: number; batch_id?: number; batch_ids?: number[]; teacher_id?: number; }

const cellKey = (batchId: number, day: string, period: number) => `${batchId}|${day}|${period}`;

export default function TimetableEditor({
  timetableId,
  onClose,
  onSaved,
}: {
  timetableId: number;
  onClose: () => void;
  onSaved?: (newId: number) => void;
}) {
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [days, setDays] = useState<string[]>([]);
  const [periods, setPeriods] = useState<PeriodRow[]>([]);
  const [batches, setBatches] = useState<BatchInfo[]>([]);
  const [subjects, setSubjects] = useState<SubjectInfo[]>([]);
  const [teachers, setTeachers] = useState<TeacherInfo[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<number | null>(null);

  const [grid, setGrid] = useState<Grid>({});
  const [past, setPast] = useState<Grid[]>([]);
  const [future, setFuture] = useState<Grid[]>([]);

  const [editing, setEditing] = useState<{ day: string; period: number } | null>(null);
  const [dragFrom, setDragFrom] = useState<{ day: string; period: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const subjectName = useCallback((id: number | null) => subjects.find((s) => s.id === id)?.name || "", [subjects]);
  const teacherName = useCallback((id: number | null) => teachers.find((t) => t.id === id)?.name || "", [teachers]);
  const batchLabel = useCallback((id: number) => {
    const b = batches.find((x) => x.id === id);
    return b ? (b.display_name || `Grade ${b.grade} - ${b.section}`) : `Class #${id}`;
  }, [batches]);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await api.timetable.getGrid(timetableId);
        setName(data.timetable?.name || "");
        setDays(data.days || []);
        setPeriods(data.periods || []);
        setBatches(data.batches || []);
        setSubjects(data.subjects || []);
        setTeachers(data.teachers || []);
        const g: Grid = {};
        for (const s of data.slots || []) {
          g[cellKey(s.batch_id, s.day, s.period_number)] = {
            subject_id: s.subject_id ?? null,
            teacher_id: s.teacher_id ?? null,
            room: s.room ?? null,
            is_lunch: !!s.is_lunch,
            is_pinned: !!s.is_pinned,
          };
        }
        setGrid(g);
        if ((data.batches || []).length) setSelectedBatch(data.batches[0].id);
      } catch (e) {
        setMessage({ kind: "err", text: "Failed to load timetable grid." });
      } finally {
        setLoading(false);
      }
    })();
  }, [timetableId]);

  // teacher_id -> set of "day|period" they cannot teach
  const teacherUnavail = useMemo(() => {
    const m: Record<number, Set<string>> = {};
    for (const t of teachers) {
      m[t.id] = new Set((t.unavailable_slots || []).map((u) => `${u.day}|${u.period}`));
    }
    return m;
  }, [teachers]);

  // Validate a grid (all batches), mirroring the backend rules. Returns the
  // human messages, the set of conflicting cell keys, and stable conflict
  // signatures used to diff "did this move introduce anything new?".
  const validateGrid = useCallback((g: Grid) => {
    const teacherSlot: Record<string, Set<number>> = {};
    const roomSlot: Record<string, Set<number>> = {};
    const out: Conflict[] = [];
    const hardCells = new Set<string>();
    const softCells = new Set<string>();
    const hardSigs = new Set<string>(); // only hard conflicts gate saving / drops

    for (const [key, c] of Object.entries(g)) {
      if (c.is_lunch || (c.subject_id == null && c.teacher_id == null)) continue;
      const [bStr, day, pStr] = key.split("|");
      const batch = Number(bStr);
      const period = Number(pStr);
      if (c.teacher_id != null) {
        const tk = `${c.teacher_id}|${day}|${period}`;
        (teacherSlot[tk] ||= new Set()).add(batch);
        if (teacherUnavail[c.teacher_id]?.has(`${day}|${period}`)) {
          out.push({ type: "teacher_unavailable", severity: "soft", message: `${teacherName(c.teacher_id)} marked ${day} P${period} unavailable — ${batchLabel(batch)} (may not be free).`, batch_id: batch, day, period });
          softCells.add(cellKey(batch, day, period));
        }
      }
      if (c.room) (roomSlot[`${c.room.trim().toLowerCase()}|${day}|${period}`] ||= new Set()).add(batch);
    }

    for (const [tk, set] of Object.entries(teacherSlot)) {
      if (set.size > 1) {
        const [tid, day, period] = tk.split("|");
        out.push({ type: "teacher_double_book", severity: "hard", message: `${teacherName(Number(tid))} is double-booked on ${day} P${period}.`, day, period: Number(period) });
        set.forEach((b) => hardCells.add(cellKey(b, day, Number(period))));
        hardSigs.add(`tdb|${tid}|${day}|${period}`);
      }
    }
    for (const [rk, set] of Object.entries(roomSlot)) {
      if (set.size > 1) {
        const [room, day, period] = rk.split("|");
        out.push({ type: "room_conflict", severity: "hard", message: `A room is double-booked on ${day} P${period}.`, day, period: Number(period) });
        set.forEach((b) => hardCells.add(cellKey(b, day, Number(period))));
        hardSigs.add(`room|${room}|${day}|${period}`);
      }
    }
    return { conflicts: out, hardCells, softCells, hardSigs };
  }, [teacherUnavail, teacherName, batchLabel]);

  const { conflicts, hardCells, softCells, hardCount } = useMemo(() => {
    const r = validateGrid(grid);
    return { conflicts: r.conflicts, hardCells: r.hardCells, softCells: r.softCells, hardCount: r.hardSigs.size };
  }, [grid, validateGrid]);

  const pushHistory = (next: Grid) => {
    setPast((p) => [...p, grid]);
    setFuture([]);
    setGrid(next);
  };
  const undo = () => {
    if (!past.length) return;
    const prev = past[past.length - 1];
    setPast((p) => p.slice(0, -1));
    setFuture((f) => [grid, ...f]);
    setGrid(prev);
  };
  const redo = () => {
    if (!future.length) return;
    const nxt = future[0];
    setFuture((f) => f.slice(1));
    setPast((p) => [...p, grid]);
    setGrid(nxt);
  };

  const batch = batches.find((b) => b.id === selectedBatch) || null;
  const batchPeriodRows = useMemo(() => {
    const cap = batch?.periods_per_day && batch.periods_per_day > 0 ? batch.periods_per_day : periods.length;
    return periods.filter((p) => p.number <= cap);
  }, [batch, periods]);

  // While dragging a period, work out which slots it can be dropped into
  // without introducing a NEW conflict, so we can highlight them in green.
  const validTargets = useMemo(() => {
    const set = new Set<string>();
    if (!dragFrom || selectedBatch == null) return set;
    const base = validateGrid(grid).hardSigs;
    const srcKey = cellKey(selectedBatch, dragFrom.day, dragFrom.period);
    const src = grid[srcKey];
    for (const p of batchPeriodRows) {
      if (p.is_lunch) continue;
      for (const day of days) {
        if (day === dragFrom.day && p.number === dragFrom.period) continue;
        const tgtKey = cellKey(selectedBatch, day, p.number);
        if (grid[tgtKey]?.is_lunch) continue;
        const next = { ...grid };
        const tgt = grid[tgtKey];
        if (tgt) next[srcKey] = tgt; else delete next[srcKey];
        if (src) next[tgtKey] = src; else delete next[tgtKey];
        const after = validateGrid(next).hardSigs;
        let ok = true;
        after.forEach((s) => { if (!base.has(s)) ok = false; });
        if (ok) set.add(tgtKey);
      }
    }
    return set;
  }, [dragFrom, grid, selectedBatch, batchPeriodRows, days, validateGrid]);

  const getCell = (day: string, period: number): Cell | null => {
    if (selectedBatch == null) return null;
    return grid[cellKey(selectedBatch, day, period)] || null;
  };

  const applyCell = (day: string, period: number, value: Partial<Cell>) => {
    if (selectedBatch == null) return;
    const key = cellKey(selectedBatch, day, period);
    const cur = grid[key] || { subject_id: null, teacher_id: null, room: null, is_lunch: false, is_pinned: false };
    const merged: Cell = { ...cur, ...value };
    const next = { ...grid };
    if (merged.subject_id == null && merged.teacher_id == null && !merged.is_lunch && !merged.is_pinned) {
      delete next[key];
    } else {
      next[key] = merged;
    }
    pushHistory(next);
  };

  const clearCell = (day: string, period: number) => {
    if (selectedBatch == null) return;
    const key = cellKey(selectedBatch, day, period);
    if (!grid[key] || grid[key].is_lunch) return;
    const next = { ...grid };
    delete next[key];
    pushHistory(next);
  };

  const togglePin = (day: string, period: number) => {
    const c = getCell(day, period);
    if (!c || c.is_lunch || c.subject_id == null) return;
    applyCell(day, period, { is_pinned: !c.is_pinned });
  };

  const swap = (a: { day: string; period: number }, b: { day: string; period: number }) => {
    if (selectedBatch == null) return;
    const ka = cellKey(selectedBatch, a.day, a.period);
    const kb = cellKey(selectedBatch, b.day, b.period);
    const ca = grid[ka];
    const cb = grid[kb];
    if (ca?.is_lunch || cb?.is_lunch) return; // never move lunch
    const next = { ...grid };
    if (cb) next[ka] = cb; else delete next[ka];
    if (ca) next[kb] = ca; else delete next[kb];
    pushHistory(next);
  };

  const onDrop = (target: { day: string; period: number }) => {
    if (dragFrom && selectedBatch != null && !(dragFrom.day === target.day && dragFrom.period === target.period)) {
      const tgtKey = cellKey(selectedBatch, target.day, target.period);
      if (!validTargets.has(tgtKey)) {
        setMessage({ kind: "err", text: "That slot isn't a valid drop — it would create a conflict. Drop onto a highlighted (green) slot." });
        setDragFrom(null);
        return;
      }
      setMessage(null);
      swap(dragFrom, target);
    }
    setDragFrom(null);
  };

  const buildSlots = () => {
    const slots: any[] = [];
    for (const [key, c] of Object.entries(grid)) {
      if (c.subject_id == null && c.teacher_id == null && !c.is_lunch) continue;
      const [b, day, p] = key.split("|");
      slots.push({
        batch_id: Number(b), day, period_number: Number(p),
        subject_id: c.subject_id, teacher_id: c.teacher_id, room: c.room,
        is_lunch: c.is_lunch, is_pinned: c.is_pinned,
      });
    }
    return slots;
  };

  const saveVersion = async () => {
    if (hardCount > 0) {
      setMessage({ kind: "err", text: "Resolve all hard conflicts (red) before saving. Availability warnings (amber) are allowed." });
      return;
    }
    try {
      setSaving(true);
      setMessage(null);
      const res = await api.timetable.saveVersion(timetableId, { slots: buildSlots() });
      setMessage({ kind: "ok", text: "Saved as a new draft version." });
      onSaved?.(res.timetable?.id);
    } catch (e: any) {
      const conf = e?.response?.data?.conflicts;
      setMessage({ kind: "err", text: conf?.length ? `Save blocked: ${conf[0].message}` : "Failed to save version." });
    } finally {
      setSaving(false);
    }
  };

  // Teacher ids already teaching some OTHER class at (day, period) => their class label.
  const slotBusyTeachers = useCallback((day: string, period: number) => {
    const m: Record<number, string> = {};
    for (const [key, c] of Object.entries(grid)) {
      if (c.is_lunch || c.teacher_id == null) continue;
      const [b, d, pStr] = key.split("|");
      if (d === day && Number(pStr) === period && Number(b) !== selectedBatch) {
        m[c.teacher_id] = batchLabel(Number(b));
      }
    }
    return m;
  }, [grid, selectedBatch, batchLabel]);

  // Teacher ids who flagged (day, period) as unavailable.
  const slotUnavailableTeachers = useCallback((day: string, period: number) => {
    const s = new Set<number>();
    for (const t of teachers) {
      if (teacherUnavail[t.id]?.has(`${day}|${period}`)) s.add(t.id);
    }
    return s;
  }, [teachers, teacherUnavail]);

  // All classes that have a teacher at a given day/period (for the exchange picker).
  const cellsAtSlot = useCallback((day: string, period: number) => {
    const list: { batchId: number; subjectId: number | null; teacherId: number | null; room: string | null }[] = [];
    for (const [key, c] of Object.entries(grid)) {
      if (c.is_lunch || c.teacher_id == null) continue;
      const [b, d, p] = key.split("|");
      if (d === day && Number(p) === period) {
        list.push({ batchId: Number(b), subjectId: c.subject_id, teacherId: c.teacher_id, room: c.room });
      }
    }
    return list.sort((a, b) => batchLabel(a.batchId).localeCompare(batchLabel(b.batchId)));
  }, [grid, batchLabel]);

  // Exchange the TEACHER of two classes at the same day/period (each class keeps
  // its own subject/room; only who teaches it is swapped).
  const exchangeTeachers = (day: string, period: number, batchA: number, batchB: number) => {
    if (batchA === batchB) return;
    const ka = cellKey(batchA, day, period);
    const kb = cellKey(batchB, day, period);
    const ca = grid[ka];
    const cb = grid[kb];
    if (!ca || !cb) return;
    const next = { ...grid };
    next[ka] = { ...ca, teacher_id: cb.teacher_id };
    next[kb] = { ...cb, teacher_id: ca.teacher_id };
    pushHistory(next);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50">
        <div className="bg-white rounded-lg px-6 py-4 shadow-xl">Loading editor…</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-3">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-6xl my-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-3">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Edit timetable</h3>
            <p className="text-xs text-slate-500">{name} — drag a period onto another to swap, click a cell to edit, 📌 to pin.</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-2xl leading-none" aria-label="Close">×</button>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 px-5 py-3 border-b bg-slate-50">
          <label className="text-sm font-medium text-slate-700">Class</label>
          <select
            value={selectedBatch ?? ""}
            onChange={(e) => { setSelectedBatch(Number(e.target.value)); setEditing(null); }}
            className="border rounded px-3 py-1.5 text-sm bg-white"
          >
            {batches.map((b) => (
              <option key={b.id} value={b.id}>{b.display_name || `Grade ${b.grade} - ${b.section}`}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button onClick={undo} disabled={!past.length} className="px-3 py-1.5 text-sm rounded border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-40">↶ Undo</button>
            <button onClick={redo} disabled={!future.length} className="px-3 py-1.5 text-sm rounded border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-40">↷ Redo</button>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {hardCount > 0 ? (
              <span className="text-sm font-medium text-red-700">{hardCount} blocking conflict(s)</span>
            ) : conflicts.length > 0 ? (
              <span className="text-sm font-medium text-amber-700">{conflicts.length} warning(s)</span>
            ) : (
              <span className="text-sm font-medium text-emerald-700">No conflicts</span>
            )}
            <button
              onClick={saveVersion}
              disabled={saving || hardCount > 0}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:text-slate-500 text-white text-sm font-medium px-4 py-1.5 rounded"
            >
              {saving ? "Saving…" : "Save as new version"}
            </button>
          </div>
        </div>

        {message && (
          <div className={`mx-5 mt-3 px-3 py-2 rounded text-sm ${message.kind === "ok" ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
            {message.text}
          </div>
        )}

        {conflicts.some((c) => c.severity === "hard") && (
          <div className="mx-5 mt-3 px-3 py-2 rounded bg-red-50 border border-red-200 text-sm text-red-800 max-h-28 overflow-y-auto">
            <div className="font-semibold mb-0.5">Must fix before saving</div>
            <ul className="list-disc list-inside space-y-0.5">
              {conflicts.filter((c) => c.severity === "hard").slice(0, 8).map((c, i) => <li key={i}>{c.message}</li>)}
            </ul>
          </div>
        )}
        {conflicts.some((c) => c.severity === "soft") && (
          <div className="mx-5 mt-3 px-3 py-2 rounded bg-amber-50 border border-amber-200 text-sm text-amber-800 max-h-28 overflow-y-auto">
            <div className="font-semibold mb-0.5">Warnings (allowed — e.g. emergency cover)</div>
            <ul className="list-disc list-inside space-y-0.5">
              {conflicts.filter((c) => c.severity === "soft").slice(0, 6).map((c, i) => <li key={i}>{c.message}</li>)}
            </ul>
          </div>
        )}

        {dragFrom && (
          <div className="mx-5 mt-3 px-3 py-2 rounded bg-emerald-50 border border-emerald-200 text-sm text-emerald-800">
            Drag in progress — <strong>green</strong> slots are valid drops (swap won't create a conflict); dimmed slots aren't.
            {validTargets.size === 0 && " No valid slot for this period in this class."}
          </div>
        )}

        {/* Grid */}
        <div className="p-5 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border bg-slate-100 px-2 py-2 text-left w-28">Period</th>
                {days.map((d) => <th key={d} className="border bg-slate-100 px-2 py-2 text-left">{d}</th>)}
              </tr>
            </thead>
            <tbody>
              {batchPeriodRows.map((p) => (
                <tr key={p.number}>
                  <td className="border bg-slate-50 px-2 py-2 align-top">
                    <div className="font-medium text-slate-700">P{p.number}</div>
                    <div className="text-[11px] text-slate-400">{p.start}–{p.end}</div>
                  </td>
                  {days.map((day) => {
                    const c = getCell(day, p.number);
                    const isLunch = p.is_lunch || c?.is_lunch;
                    const ckey = selectedBatch != null ? cellKey(selectedBatch, day, p.number) : "";
                    const hardConflicted = !!ckey && hardCells.has(ckey);
                    const softConflicted = !!ckey && softCells.has(ckey);
                    if (isLunch) {
                      return <td key={day} className="border px-2 py-3 text-center text-amber-700 bg-amber-50 font-medium">Lunch</td>;
                    }
                    const filled = c && (c.subject_id != null || c.teacher_id != null);
                    const key = cellKey(selectedBatch!, day, p.number);
                    const isSource = dragFrom && dragFrom.day === day && dragFrom.period === p.number;
                    const dragging = !!dragFrom;
                    const isValidTarget = dragging && validTargets.has(key);
                    let stateClass: string;
                    if (isSource) {
                      stateClass = "bg-blue-100 ring-2 ring-blue-500";
                    } else if (dragging && isValidTarget) {
                      stateClass = "bg-emerald-50 ring-2 ring-emerald-400 hover:bg-emerald-100";
                    } else if (dragging) {
                      stateClass = "opacity-40"; // not a valid drop while dragging
                    } else if (hardConflicted) {
                      stateClass = "bg-red-50 ring-1 ring-red-300";
                    } else if (softConflicted) {
                      stateClass = "bg-amber-50 ring-1 ring-amber-300";
                    } else if (filled) {
                      stateClass = "bg-white hover:bg-blue-50";
                    } else {
                      stateClass = "bg-slate-50 hover:bg-blue-50 text-slate-400";
                    }
                    return (
                      <td
                        key={day}
                        draggable={!!filled}
                        onDragStart={() => filled && setDragFrom({ day, period: p.number })}
                        onDragEnd={() => setDragFrom(null)}
                        onDragOver={(e) => { if (isValidTarget) e.preventDefault(); }}
                        onDrop={() => onDrop({ day, period: p.number })}
                        onClick={() => !dragging && setEditing({ day, period: p.number })}
                        className={`border px-2 py-2 align-top cursor-pointer min-w-[130px] transition ${stateClass}`}
                      >
                        {filled ? (
                          <div>
                            <div className="flex items-start justify-between gap-1">
                              <span className="font-medium text-slate-800">{subjectName(c!.subject_id) || "—"}</span>
                              <button
                                onClick={(e) => { e.stopPropagation(); togglePin(day, p.number); }}
                                title={c!.is_pinned ? "Unpin" : "Pin (kept on regeneration)"}
                                className={c!.is_pinned ? "text-amber-500" : "text-slate-300 hover:text-amber-500"}
                              >📌</button>
                            </div>
                            <div className="text-xs text-slate-500">{teacherName(c!.teacher_id) || "No teacher"}</div>
                            {c!.room && <div className="text-[11px] text-slate-400">🚪 {c!.room}</div>}
                          </div>
                        ) : (
                          <span className="text-xs">+ add</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cell editor popover */}
      {editing && selectedBatch != null && (
        <CellEditor
          day={editing.day}
          period={editing.period}
          cell={getCell(editing.day, editing.period)}
          subjects={subjects}
          teachers={teachers}
          slotBusy={slotBusyTeachers(editing.day, editing.period)}
          unavailableAt={slotUnavailableTeachers(editing.day, editing.period)}
          exchangeOptions={cellsAtSlot(editing.day, editing.period).filter((c) => c.batchId !== selectedBatch)}
          batchLabel={batchLabel}
          subjectName={subjectName}
          teacherName={teacherName}
          onExchange={(otherBatchId) => { exchangeTeachers(editing.day, editing.period, selectedBatch, otherBatchId); setEditing(null); }}
          onApply={(value) => { applyCell(editing.day, editing.period, value); setEditing(null); }}
          onClear={() => { clearCell(editing.day, editing.period); setEditing(null); }}
          onTogglePin={() => { togglePin(editing.day, editing.period); }}
          onCancel={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function CellEditor({
  day, period, cell, subjects, teachers, slotBusy, unavailableAt,
  exchangeOptions, batchLabel, subjectName, teacherName, onExchange,
  onApply, onClear, onTogglePin, onCancel,
}: {
  day: string; period: number; cell: Cell | null;
  subjects: SubjectInfo[];
  teachers: TeacherInfo[];
  slotBusy: Record<number, string>;     // teacher id -> class they already teach this slot
  unavailableAt: Set<number>;           // teacher ids who flagged this slot unavailable
  exchangeOptions: { batchId: number; subjectId: number | null; teacherId: number | null; room: string | null }[];
  batchLabel: (id: number) => string;
  subjectName: (id: number | null) => string;
  teacherName: (id: number | null) => string;
  onExchange: (otherBatchId: number) => void;
  onApply: (value: Partial<Cell>) => void;
  onClear: () => void;
  onTogglePin: () => void;
  onCancel: () => void;
}) {
  const [subjectId, setSubjectId] = useState<number | null>(cell?.subject_id ?? null);
  const [teacherId, setTeacherId] = useState<number | null>(cell?.teacher_id ?? null);
  const [room, setRoom] = useState<string>(cell?.room ?? "");
  const [exchangeWith, setExchangeWith] = useState<number | "">("");

  const label = (t: TeacherInfo) => (t.teacher_code ? `${t.teacher_code} — ${t.name}` : t.name);

  // Base pool: teachers who can teach the chosen subject (if any are capable),
  // otherwise everyone. Then split by availability at THIS day/period.
  const capable = subjectId == null ? teachers : teachers.filter((t) => (t.subject_ids || []).includes(subjectId));
  const base = capable.length ? capable : teachers;
  const free = base.filter((t) => !slotBusy[t.id] && !unavailableAt.has(t.id));
  const emergency = base.filter((t) => !slotBusy[t.id] && unavailableAt.has(t.id));
  const busy = base.filter((t) => !!slotBusy[t.id]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/40" onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-sm p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-slate-900">{day} · Period {period}</h4>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-700 text-xl leading-none">×</button>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Subject</label>
          <select value={subjectId ?? ""} onChange={(e) => setSubjectId(e.target.value ? Number(e.target.value) : null)} className="w-full border rounded px-3 py-2 text-sm">
            <option value="">— none —</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Teacher (availability for {day} P{period})</label>
          <select value={teacherId ?? ""} onChange={(e) => setTeacherId(e.target.value ? Number(e.target.value) : null)} className="w-full border rounded px-3 py-2 text-sm">
            <option value="">— none —</option>
            {free.length > 0 && (
              <optgroup label={`Available (${free.length})`}>
                {free.map((t) => <option key={t.id} value={t.id}>{label(t)}</option>)}
              </optgroup>
            )}
            {emergency.length > 0 && (
              <optgroup label={`Free but marked unavailable (${emergency.length})`}>
                {emergency.map((t) => <option key={t.id} value={t.id}>⚠ {label(t)} — may be unavailable</option>)}
              </optgroup>
            )}
            {busy.length > 0 && (
              <optgroup label={`Busy this period (${busy.length})`}>
                {busy.map((t) => <option key={t.id} value={t.id} disabled>{label(t)} — teaching {slotBusy[t.id]}</option>)}
              </optgroup>
            )}
          </select>
          <p className="text-[11px] text-slate-400 mt-1">
            <span className="text-emerald-600">Available</span> = free &amp; not flagged · <span className="text-amber-600">⚠</span> free but marked unavailable (emergency only) · busy teachers are disabled.
          </p>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Room (optional)</label>
          <input value={room} onChange={(e) => setRoom(e.target.value)} placeholder="e.g. Lab 1, R204" className="w-full border rounded px-3 py-2 text-sm" />
        </div>

        {/* Quick exchange: only need to pick the other teacher; their class at
            this same time is swapped with this one automatically. */}
        {cell?.teacher_id != null && (
          <div className="border-t pt-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">🔁 Exchange with another teacher (same time)</label>
            {exchangeOptions.length === 0 ? (
              <p className="text-xs text-slate-400">No other class has a teacher at {day} P{period}.</p>
            ) : (
              <div className="flex gap-2">
                <select value={exchangeWith} onChange={(e) => setExchangeWith(e.target.value ? Number(e.target.value) : "")} className="flex-1 border rounded px-3 py-2 text-sm">
                  <option value="">Select a teacher to swap with…</option>
                  {exchangeOptions.map((c) => (
                    <option key={c.batchId} value={c.batchId}>
                      {teacherName(c.teacherId)} — {batchLabel(c.batchId)} ({subjectName(c.subjectId) || "—"})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => exchangeWith !== "" && onExchange(exchangeWith as number)}
                  disabled={exchangeWith === ""}
                  className="px-3 py-2 text-sm rounded bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:text-slate-500 text-white whitespace-nowrap"
                >
                  Exchange
                </button>
              </div>
            )}
            <p className="text-[11px] text-slate-400 mt-1">{teacherName(cell.teacher_id)} ↔ the selected teacher swap classes for this period.</p>
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <button onClick={onTogglePin} className="text-sm text-amber-600 hover:underline">{cell?.is_pinned ? "Unpin 📌" : "Pin 📌"}</button>
          <div className="flex gap-2">
            <button onClick={onClear} className="px-3 py-1.5 text-sm rounded border border-slate-300 hover:bg-slate-100">Clear</button>
            <button
              onClick={() => onApply({ subject_id: subjectId, teacher_id: teacherId, room: room.trim() || null })}
              className="px-4 py-1.5 text-sm rounded bg-blue-600 hover:bg-blue-700 text-white"
            >
              Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
