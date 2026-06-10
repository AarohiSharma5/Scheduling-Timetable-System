import React, { useState } from "react";
import { api } from "../api";

/** Pre-flight feasibility check shown above the Generate button.
 *
 * Runs the same capacity-aware plan the engine uses, so what it reports is
 * exactly what generation will do: per-class period budgets vs subject demand,
 * teacher supply per subject, and one-click charge rebalancing that moves
 * non-teaching duties off overloaded subject teachers (class-teachership is
 * never moved).
 */

interface ClassRow {
  batch_id: number;
  label: string;
  budget: number;
  demand: number;
  free: number;
  status: "ok" | "tight" | "over";
  subjects: { subject_id: number; subject: string; periods: number }[];
  impossible: string[];
}

interface SubjectRow {
  subject_id: number;
  subject: string;
  demand: number;
  sections: number;
  teachers: number;
  deficit: number;
  unstaffed_sections: string[];
  status: "ok" | "short" | "unstaffed";
}

interface TeacherLoadRow {
  teacher_id: number;
  name: string;
  planned: number;
  capacity: number;
  charge_hours: number;
  is_class_teacher: boolean;
  status: "ok" | "full" | "over";
}

interface Move {
  from_teacher_id: number;
  from_name: string;
  to_teacher_id: number;
  to_name: string;
  charge_name: string;
  hours: number;
  reason: string;
}

interface RoomRow {
  room_type: string;
  rooms: number;
  demand: number;
  supply: number;
  status: "ok" | "over";
}

interface Audit {
  ok: boolean;
  error?: string;
  summary?: {
    classes_total: number;
    classes_over_budget: number;
    subjects_short: number;
    subjects_unstaffed: number;
    teachers_overloaded: number;
    rooms_over_capacity?: number;
    total_capacity_deficit: number;
    rebalance_can_free: number;
    rebalance_covers_deficit: boolean;
  };
  classes?: ClassRow[];
  subjects?: SubjectRow[];
  teacher_loads?: TeacherLoadRow[];
  rooms?: RoomRow[];
  rebalance_suggestions?: Move[];
}

export default function FeasibilityPanel() {
  const [audit, setAudit] = useState<Audit | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const run = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const data = await api.timetable.feasibility();
      setAudit(data);
      setShowDetails(!data.ok);
    } catch (e: any) {
      setMessage(e.response?.data?.error || e.message);
    } finally {
      setLoading(false);
    }
  };

  const applyRebalance = async () => {
    if (!audit?.rebalance_suggestions?.length) return;
    setApplying(true);
    setMessage(null);
    try {
      const res = await api.timetable.rebalanceCharges(audit.rebalance_suggestions);
      setMessage(res.message);
      // Re-run the audit to show the post-move picture.
      const data = await api.timetable.feasibility();
      setAudit(data);
      setShowDetails(!data.ok);
    } catch (e: any) {
      setMessage(e.response?.data?.error || e.message);
    } finally {
      setApplying(false);
    }
  };

  const s = audit?.summary;
  const problemClasses = (audit?.classes || []).filter(
    (c) => c.status === "over" || c.impossible.length > 0
  );
  const problemSubjects = (audit?.subjects || []).filter((x) => x.status !== "ok");
  const overloaded = (audit?.teacher_loads || []).filter((t) => t.status === "over");
  const problemRooms = (audit?.rooms || []).filter((r) => r.status === "over");

  return (
    <div className="bg-white rounded-lg p-6 border-2 border-slate-200">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Pre-flight Check</h2>
          <p className="text-sm text-slate-600 mt-1">
            Verify every class's weekly periods fit its day and every subject has enough
            teacher capacity — before generating.
          </p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white font-semibold py-2 px-5 rounded-lg transition"
        >
          {loading ? "Checking…" : "Run feasibility check"}
        </button>
      </div>

      {message && (
        <div className="mt-4 p-3 rounded text-sm bg-blue-50 border border-blue-200 text-blue-900">
          {message}
        </div>
      )}

      {audit?.error && (
        <div className="mt-4 p-3 rounded text-sm bg-red-50 border border-red-200 text-red-800">
          {audit.error}
        </div>
      )}

      {audit && !audit.error && s && (
        <div className="mt-4 space-y-4">
          {/* Verdict banner */}
          <div
            className={`p-4 rounded-lg border ${
              audit.ok
                ? "bg-green-50 border-green-300 text-green-900"
                : "bg-amber-50 border-amber-300 text-amber-900"
            }`}
          >
            <div className="font-bold">
              {audit.ok
                ? "✓ Feasible — class budgets, teacher capacity and rooms all check out."
                : "⚠ Issues found — generation will leave gaps unless these are fixed."}
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium">
              <span className="px-2 py-1 rounded bg-white/70 border border-current/20">
                {s.classes_total} classes · {s.classes_over_budget} over budget
              </span>
              <span className="px-2 py-1 rounded bg-white/70 border border-current/20">
                {s.subjects_short} subjects short of capacity
              </span>
              <span className="px-2 py-1 rounded bg-white/70 border border-current/20">
                {s.subjects_unstaffed} unstaffed
              </span>
              <span className="px-2 py-1 rounded bg-white/70 border border-current/20">
                {s.teachers_overloaded} teachers overloaded
              </span>
              {s.total_capacity_deficit > 0 && (
                <span className="px-2 py-1 rounded bg-white/70 border border-current/20">
                  {s.total_capacity_deficit} period(s)/week missing
                </span>
              )}
            </div>
          </div>

          {/* One-click charge rebalancing */}
          {(audit.rebalance_suggestions?.length || 0) > 0 && (
            <div className="p-4 rounded-lg border border-indigo-300 bg-indigo-50">
              <div className="font-bold text-indigo-900">
                Fix available: move non-teaching charges
              </div>
              <p className="text-sm text-indigo-800 mt-1">
                Core-subject periods are never reduced. Instead, hand these duties to
                colleagues with lighter timetables to free up{" "}
                <strong>{s.rebalance_can_free} period(s)/week</strong>
                {s.rebalance_covers_deficit ? " — enough to cover the whole gap." : "."}
                {" "}Class-teachership is never moved.
              </p>
              <ul className="mt-2 space-y-1 text-sm text-indigo-900">
                {audit.rebalance_suggestions!.map((m, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-0.5">↪</span>
                    <span>
                      <strong>{m.charge_name}</strong> ({m.hours}h/wk): {m.from_name} →{" "}
                      {m.to_name}
                      <span className="text-indigo-600"> — {m.reason}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <button
                onClick={applyRebalance}
                disabled={applying}
                className="mt-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white text-sm font-semibold py-2 px-4 rounded-lg transition"
              >
                {applying ? "Applying…" : "Apply charge rebalancing"}
              </button>
            </div>
          )}

          {/* Details */}
          <button
            onClick={() => setShowDetails((v) => !v)}
            className="text-sm font-semibold text-slate-600 hover:text-slate-900"
          >
            {showDetails ? "▾ Hide details" : "▸ Show details"}
          </button>

          {showDetails && (
            <div className="space-y-4">
              {/* Class budget problems */}
              {problemClasses.length > 0 && (
                <div>
                  <h3 className="font-bold text-slate-800 text-sm mb-2">
                    Classes whose subjects don't fit the week
                  </h3>
                  <div className="space-y-2">
                    {problemClasses.map((c) => (
                      <div
                        key={c.batch_id}
                        className="p-3 rounded border border-red-200 bg-red-50 text-sm"
                      >
                        <div className="font-semibold text-red-900">
                          {c.label}: needs {c.demand} periods, week has {c.budget}
                          {c.demand > c.budget && (
                            <span> — remove {c.demand - c.budget} period(s) of low-priority subjects or lengthen the day</span>
                          )}
                        </div>
                        {c.impossible.map((line, i) => (
                          <div key={i} className="text-red-700 mt-1">⛔ {line}</div>
                        ))}
                        <div className="mt-1 text-red-800/80">
                          {c.subjects.map((sub) => `${sub.subject} ${sub.periods}`).join(" · ")}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Subject supply problems */}
              {problemSubjects.length > 0 && (
                <div>
                  <h3 className="font-bold text-slate-800 text-sm mb-2">
                    Subjects without enough teacher capacity
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm border border-slate-200 rounded">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr>
                          <th className="px-3 py-2 text-left">Subject</th>
                          <th className="px-3 py-2 text-right">Demand/wk</th>
                          <th className="px-3 py-2 text-right">Sections</th>
                          <th className="px-3 py-2 text-right">Teachers</th>
                          <th className="px-3 py-2 text-left">Problem</th>
                        </tr>
                      </thead>
                      <tbody>
                        {problemSubjects.map((x) => (
                          <tr key={x.subject_id} className="border-t border-slate-100">
                            <td className="px-3 py-2 font-medium">{x.subject}</td>
                            <td className="px-3 py-2 text-right">{x.demand}</td>
                            <td className="px-3 py-2 text-right">{x.sections}</td>
                            <td className="px-3 py-2 text-right">{x.teachers}</td>
                            <td className="px-3 py-2 text-red-700">
                              {x.status === "unstaffed"
                                ? `No eligible teacher for: ${x.unstaffed_sections.join(", ")}`
                                : `${x.deficit} period(s)/week over teacher capacity`}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Shared special rooms over capacity */}
              {problemRooms.length > 0 && (
                <div>
                  <h3 className="font-bold text-slate-800 text-sm mb-2">
                    Shared rooms over capacity
                  </h3>
                  <div className="space-y-1">
                    {problemRooms.map((r) => (
                      <div
                        key={r.room_type}
                        className="p-2 rounded border border-orange-200 bg-orange-50 text-sm text-orange-900"
                      >
                        <strong className="capitalize">{r.room_type}</strong>: {r.demand}{" "}
                        periods/week need it but only {r.supply} room-slots exist ({r.rooms}{" "}
                        room{r.rooms === 1 ? "" : "s"}) — add another room or reduce those
                        subjects' periods.
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Overloaded teachers */}
              {overloaded.length > 0 && (
                <div>
                  <h3 className="font-bold text-slate-800 text-sm mb-2">Overloaded teachers</h3>
                  <div className="flex flex-wrap gap-2">
                    {overloaded.map((t) => (
                      <span
                        key={t.teacher_id}
                        className="px-2 py-1 rounded bg-red-50 border border-red-200 text-red-800 text-xs"
                      >
                        {t.name}: {t.planned}/{t.capacity} planned
                        {t.charge_hours > 0 && ` (+${t.charge_hours}h charges)`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {audit.ok && (
                <p className="text-sm text-green-700">
                  All classes fit their weekly budget and every subject is staffed within
                  teacher capacity.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
