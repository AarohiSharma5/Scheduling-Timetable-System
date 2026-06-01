import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Row {
  id?: number;
  subject_id: number;
  name: string;
  subject_type?: string;
  periods_per_week: number;
  min_periods: number | null;
  max_periods: number | null;
  max_per_day: number;
  allow_consecutive: boolean;
  allow_daily: boolean;
  priority: "high" | "medium" | "low";
  preferred_spread: string;
  configured: boolean; // has a saved per-class override
}

const PRIORITY_STYLE: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-300",
  medium: "bg-slate-100 text-slate-700 border-slate-300",
  low: "bg-blue-100 text-blue-700 border-blue-300",
};

export default function ClassPeriodConfig() {
  const [grades, setGrades] = useState<string[]>([]);
  const [grade, setGrade] = useState<string>("");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [validation, setValidation] = useState<any>(null);

  useEffect(() => {
    api.admin.classSubjectConfig
      .list()
      .then((d) => {
        setGrades(d.grades || []);
        if ((d.grades || []).length && !grade) setGrade(d.grades[0]);
      })
      .catch(() => setErr("Failed to load grades"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (grade) loadGrade(grade);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grade]);

  const loadGrade = async (g: string) => {
    try {
      setLoading(true);
      setMsg("");
      setErr("");
      const d = await api.admin.classSubjectConfig.list(g);
      const cfgBySub: Record<number, any> = {};
      (d.configs || []).forEach((c: any) => (cfgBySub[c.subject_id] = c));
      const merged: Row[] = (d.subjects_for_grade || []).map((s: any) => {
        const c = cfgBySub[s.subject_id];
        return {
          id: c?.id,
          subject_id: s.subject_id,
          name: s.name,
          subject_type: s.subject_type,
          periods_per_week: c?.periods_per_week ?? s.periods_per_week ?? 1,
          min_periods: c?.min_periods ?? null,
          max_periods: c?.max_periods ?? null,
          max_per_day: c?.max_per_day ?? s.max_periods_per_day ?? 1,
          allow_consecutive: c?.allow_consecutive ?? false,
          allow_daily: c?.allow_daily ?? true,
          priority: (c?.priority as Row["priority"]) ?? "medium",
          preferred_spread: c?.preferred_spread ?? "even",
          configured: !!c,
        };
      });
      setRows(merged);
    } catch (e) {
      setErr("Failed to load class configuration");
    } finally {
      setLoading(false);
    }
  };

  const update = (idx: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r, i) => (i === idx ? { ...r, ...patch } : r)));

  const save = async () => {
    try {
      setSaving(true);
      setMsg("");
      setErr("");
      await api.admin.classSubjectConfig.save(
        grade,
        rows.map((r) => ({
          subject_id: r.subject_id,
          periods_per_week: r.periods_per_week,
          min_periods: r.min_periods,
          max_periods: r.max_periods,
          max_per_day: r.max_per_day,
          allow_consecutive: r.allow_consecutive,
          allow_daily: r.allow_daily,
          priority: r.priority,
          preferred_spread: r.preferred_spread,
        }))
      );
      setMsg(`Saved configuration for Grade ${grade}.`);
      await loadGrade(grade);
    } catch (e) {
      setErr("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const runValidation = async () => {
    try {
      setErr("");
      const r = await api.admin.classSubjectConfig.validatePlanning();
      setValidation(r);
    } catch (e) {
      setErr("Validation failed (generate a timetable first)");
    }
  };

  const totalWeekly = rows.reduce((sum, r) => sum + (Number(r.periods_per_week) || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Class Period Planning</h2>
          <p className="text-sm text-slate-500">
            Per-class subject frequency, daily limits, consecutiveness and priority.
            Blank rows fall back to the org-wide subject defaults.
          </p>
        </div>
        <button
          onClick={runValidation}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
        >
          Validate latest timetable
        </button>
      </div>

      {err && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{err}</div>}
      {msg && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">{msg}</div>}

      {validation && (
        <div className={`border rounded-lg p-4 ${validation.ok ? "bg-green-50 border-green-300" : "bg-amber-50 border-amber-300"}`}>
          <h4 className="font-semibold text-slate-900 mb-2">
            Planning validation — {validation.ok ? "all checks passed ✅" : "issues found ⚠️"}
          </h4>
          <ul className="text-sm text-slate-700 space-y-1">
            <li>Mode: <strong>{validation.generation_mode}</strong></li>
            <li>Subject weekly-count shortfalls: <strong>{validation.shortfall_total}</strong></li>
            <li>Teacher double-bookings: <strong>{(validation.teacher_double_bookings || []).length}</strong></li>
            <li>Assembly: {validation.assembly?.note}</li>
            <li>Zero period: {validation.zero_period?.note}</li>
            <li>Class-teacher-first: {validation.class_teacher_first?.note}</li>
          </ul>
          {(validation.subject_count_shortfalls || []).length > 0 && (
            <details className="mt-2">
              <summary className="text-sm text-slate-600 cursor-pointer">Show shortfalls</summary>
              <div className="text-xs text-slate-600 mt-1 max-h-40 overflow-auto">
                {validation.subject_count_shortfalls.map((s: any, i: number) => (
                  <div key={i}>{s.class}: {s.subject} {s.scheduled}/{s.required}</div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-slate-700">Grade / class</label>
        <select value={grade} onChange={(e) => setGrade(e.target.value)} className="border rounded px-3 py-2">
          {grades.map((g) => (
            <option key={g} value={g}>Grade {g}</option>
          ))}
        </select>
        <span className="text-sm text-slate-500">Total: <strong>{totalWeekly}</strong> periods/week</span>
      </div>

      {loading ? (
        <div className="text-center py-6 text-slate-500">Loading…</div>
      ) : rows.length === 0 ? (
        <div className="text-center py-6 text-slate-500">No subjects assigned to this grade yet.</div>
      ) : (
        <div className="bg-white rounded-lg shadow-md overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Subject</th>
                <th className="px-3 py-2">Per week</th>
                <th className="px-3 py-2">Min</th>
                <th className="px-3 py-2">Max</th>
                <th className="px-3 py-2">Max/day</th>
                <th className="px-3 py-2">Consecutive</th>
                <th className="px-3 py-2">Daily ok</th>
                <th className="px-3 py-2">Priority</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={r.subject_id} className="border-t">
                  <td className="px-3 py-2 font-medium text-slate-800">
                    {r.name}
                    {r.subject_type && r.subject_type !== "core" && (
                      <span className="ml-2 text-xs text-slate-400">({r.subject_type})</span>
                    )}
                    {r.configured && <span className="ml-2 text-xs text-green-600">●</span>}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input type="number" min={0} value={r.periods_per_week}
                      onChange={(e) => update(idx, { periods_per_week: Number(e.target.value) })}
                      className="border rounded w-16 px-2 py-1 text-center" />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input type="number" min={0} value={r.min_periods ?? ""}
                      onChange={(e) => update(idx, { min_periods: e.target.value === "" ? null : Number(e.target.value) })}
                      className="border rounded w-14 px-2 py-1 text-center" />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input type="number" min={0} value={r.max_periods ?? ""}
                      onChange={(e) => update(idx, { max_periods: e.target.value === "" ? null : Number(e.target.value) })}
                      className="border rounded w-14 px-2 py-1 text-center" />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input type="number" min={1} value={r.max_per_day}
                      onChange={(e) => update(idx, { max_per_day: Number(e.target.value) })}
                      className="border rounded w-14 px-2 py-1 text-center" />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input type="checkbox" checked={r.allow_consecutive}
                      onChange={(e) => update(idx, { allow_consecutive: e.target.checked })} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <input type="checkbox" checked={r.allow_daily}
                      onChange={(e) => update(idx, { allow_daily: e.target.checked })} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <select value={r.priority}
                      onChange={(e) => update(idx, { priority: e.target.value as Row["priority"] })}
                      className={`border rounded px-2 py-1 text-xs ${PRIORITY_STYLE[r.priority]}`}>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rows.length > 0 && (
        <button onClick={save} disabled={saving}
          className="bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-medium px-6 py-2.5 rounded-lg">
          {saving ? "Saving…" : `Save Grade ${grade} configuration`}
        </button>
      )}
    </div>
  );
}
