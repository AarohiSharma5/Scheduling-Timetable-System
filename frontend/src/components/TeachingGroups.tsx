import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

interface Group {
  id: number;
  name: string;
  grade: string;
  stream: string | null;
  section: string | null;
  group_type: string;
  subject_id: number | null;
  teacher_id: number | null;
  room_id: number | null;
  periods_per_week: number | null;
  block_key: string | null;
  locked: boolean;
  auto_generated: boolean;
  student_count: number;
}

interface Member {
  student_id: number;
  name: string | null;
  section: string | null;
  roll_no: number | null;
}

interface Lite {
  id: number;
  name?: string;
  room_name?: string;
}

const TYPE_BADGE: Record<string, string> = {
  homeroom: "bg-slate-100 text-slate-700",
  elective: "bg-indigo-100 text-indigo-800",
  language: "bg-amber-100 text-amber-800",
  core: "bg-emerald-100 text-emerald-800",
  combination: "bg-purple-100 text-purple-800",
};

export default function TeachingGroups() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [teachers, setTeachers] = useState<Lite[]>([]);
  const [subjects, setSubjects] = useState<Lite[]>([]);
  const [rooms, setRooms] = useState<Lite[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [validation, setValidation] = useState<any | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const teacherName = (id: number | null) => teachers.find((t) => t.id === id)?.name || "—";
  const subjectName = (id: number | null) => subjects.find((s) => s.id === id)?.name || "—";
  const roomName = (id: number | null) => rooms.find((r) => r.id === id)?.room_name || "—";

  const loadAll = async () => {
    setLoading(true);
    try {
      const [g, t, s, r] = await Promise.all([
        api.admin.teachingGroups.list(),
        api.admin.teachers.list(),
        api.admin.subjects.list(),
        api.admin.rooms.list().catch(() => []),
      ]);
      setGroups(g || []);
      setTeachers(t || []);
      setSubjects(s || []);
      setRooms(r || []);
    } catch (e: any) {
      setError(e?.response?.data?.error || "Failed to load teaching groups");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const generate = async () => {
    if (!window.confirm("Rebuild teaching groups from current student stream/elective choices? Locked groups are kept.")) return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await api.admin.teachingGroups.generate();
      setWarnings(res.warnings || []);
      setInfo(
        `Created ${res.created} groups (${res.counts?.homeroom || 0} homeroom, ` +
          `${res.counts?.elective || 0} elective, ${res.counts?.language || 0} language). ` +
          `${res.locked_kept ? res.locked_kept + " locked kept." : ""}`
      );
      await loadAll();
    } catch (e: any) {
      setError(e?.response?.data?.error || "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const runValidation = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.admin.teachingGroups.validate();
      setValidation(res);
    } catch (e: any) {
      setError(e?.response?.data?.error || "Validation failed (generate a timetable first)");
    } finally {
      setBusy(false);
    }
  };

  const patch = async (id: number, updates: any) => {
    try {
      await api.admin.teachingGroups.update(id, updates);
      setGroups((gs) => gs.map((g) => (g.id === id ? { ...g, ...updates } : g)));
    } catch (e: any) {
      setError(e?.response?.data?.error || "Update failed");
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this group?")) return;
    try {
      await api.admin.teachingGroups.delete(id);
      setGroups((gs) => gs.filter((g) => g.id !== id));
    } catch (e: any) {
      setError(e?.response?.data?.error || "Delete failed");
    }
  };

  const toggleMembers = async (id: number) => {
    if (expanded === id) {
      setExpanded(null);
      setMembers([]);
      return;
    }
    try {
      const full = await api.admin.teachingGroups.get(id);
      setMembers(full.members || []);
      setExpanded(id);
    } catch {
      setMembers([]);
    }
  };

  const filtered = useMemo(
    () => (typeFilter === "all" ? groups : groups.filter((g) => g.group_type === typeFilter)),
    [groups, typeFilter]
  );

  const byGrade = useMemo(() => {
    const m: Record<string, Group[]> = {};
    filtered.forEach((g) => {
      (m[g.grade] = m[g.grade] || []).push(g);
    });
    return Object.entries(m).sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }));
  }, [filtered]);

  if (loading) return <div className="p-6 text-slate-500">Loading teaching groups…</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Teaching Groups</h2>
          <p className="text-sm text-slate-500">
            Homeroom sections plus cross-section elective &amp; language groups. Electives in a grade
            run in one parallel block, so no student ever clashes.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runValidation}
            disabled={busy}
            className="px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50"
          >
            Validate coverage
          </button>
          <button
            onClick={generate}
            disabled={busy}
            className="px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Working…" : "Generate groups"}
          </button>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 text-red-700 px-4 py-2 text-sm">{error}</div>}
      {info && <div className="rounded-lg bg-indigo-50 text-indigo-700 px-4 py-2 text-sm">{info}</div>}

      {validation && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${validation.ok ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
          <div className="font-semibold text-slate-800">
            No-class-loss check — {validation.students_ok}/{validation.students_total} students fully covered
          </div>
          <div className="mt-1 text-slate-600">
            Missing core: {validation.counts?.missing_core} · Missing elective:{" "}
            {validation.counts?.missing_elective} · Overlaps: {validation.counts?.overlaps}
          </div>
          {validation.issues_sample?.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-slate-600 max-h-40 overflow-auto">
              {validation.issues_sample.slice(0, 8).map((it: any, i: number) => (
                <li key={i}>
                  <span className="font-medium">{it.class}</span> — {it.problems.join("; ")}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <div className="font-semibold">Formation notes ({warnings.length})</div>
          <ul className="mt-1 list-disc pl-5 max-h-40 overflow-auto">
            {warnings.slice(0, 12).map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2 text-sm">
        {["all", "homeroom", "elective", "language"].map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded-full border ${
              typeFilter === t ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-300"
            }`}
          >
            {t === "all" ? "All" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {groups.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-slate-500">
          No teaching groups yet. Set student streams/electives, then click <b>Generate groups</b>.
        </div>
      )}

      {byGrade.map(([grade, gs]) => (
        <div key={grade} className="rounded-xl border border-slate-200 bg-white">
          <div className="px-4 py-2 border-b border-slate-100 font-semibold text-slate-700">Grade {grade}</div>
          <div className="divide-y divide-slate-100">
            {gs.map((g) => (
              <div key={g.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_BADGE[g.group_type] || "bg-slate-100 text-slate-700"}`}>
                    {g.group_type}
                  </span>
                  <span className="font-medium text-slate-800">{g.name}</span>
                  <span className="text-xs text-slate-500">{g.student_count} students</span>
                  {g.block_key && <span className="text-xs text-slate-400">block: {g.block_key}</span>}
                  {g.locked && <span className="text-xs text-rose-600 font-semibold">🔒 locked</span>}
                  <button
                    onClick={() => toggleMembers(g.id)}
                    className="ml-auto text-xs text-indigo-600 hover:underline"
                  >
                    {expanded === g.id ? "Hide students" : "View students"}
                  </button>
                </div>

                {g.group_type !== "homeroom" && (
                  <div className="mt-2 grid grid-cols-1 sm:grid-cols-4 gap-2 text-sm">
                    <label className="flex flex-col">
                      <span className="text-xs text-slate-500">Subject</span>
                      <span className="text-slate-700">{subjectName(g.subject_id)}</span>
                    </label>
                    <label className="flex flex-col">
                      <span className="text-xs text-slate-500">Teacher</span>
                      <select
                        value={g.teacher_id ?? ""}
                        onChange={(e) => patch(g.id, { teacher_id: e.target.value ? Number(e.target.value) : null })}
                        className="border border-slate-300 rounded px-2 py-1 text-slate-700"
                      >
                        <option value="">— unassigned —</option>
                        {teachers.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="flex flex-col">
                      <span className="text-xs text-slate-500">Room</span>
                      <select
                        value={g.room_id ?? ""}
                        onChange={(e) => patch(g.id, { room_id: e.target.value ? Number(e.target.value) : null })}
                        className="border border-slate-300 rounded px-2 py-1 text-slate-700"
                      >
                        <option value="">— none —</option>
                        {rooms.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.room_name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="flex flex-col">
                      <span className="text-xs text-slate-500">Periods/week</span>
                      <input
                        type="number"
                        min={0}
                        value={g.periods_per_week ?? ""}
                        onChange={(e) => patch(g.id, { periods_per_week: e.target.value ? Number(e.target.value) : null })}
                        className="border border-slate-300 rounded px-2 py-1 text-slate-700 w-24"
                      />
                    </label>
                  </div>
                )}

                {g.group_type !== "homeroom" && (
                  <div className="mt-2 flex gap-3 text-xs">
                    <button onClick={() => patch(g.id, { locked: !g.locked })} className="text-slate-600 hover:underline">
                      {g.locked ? "Unlock" : "Lock before generation"}
                    </button>
                    <button onClick={() => remove(g.id)} className="text-rose-600 hover:underline">
                      Delete
                    </button>
                  </div>
                )}

                {expanded === g.id && (
                  <div className="mt-3 rounded-lg bg-slate-50 p-3">
                    {members.length === 0 ? (
                      <div className="text-xs text-slate-500">No students.</div>
                    ) : (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 text-xs text-slate-600 max-h-48 overflow-auto">
                        {members.map((m) => (
                          <div key={m.student_id} className="truncate">
                            {m.name} <span className="text-slate-400">({m.section}{m.roll_no ? `·${m.roll_no}` : ""})</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
