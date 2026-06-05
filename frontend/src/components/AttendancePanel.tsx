import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

interface ClassItem {
  batch_id: number;
  grade: string;
  section: string;
  label: string;
  student_count: number;
}

interface RosterRow {
  student_id: number;
  name: string;
  roll_no: number | null;
  admission_no: string;
  status: string;
  remarks: string | null;
  marked: boolean;
}

interface SummaryRow {
  student_id: number;
  name: string;
  roll_no: number | null;
  present: number;
  absent: number;
  late: number;
  excused: number;
  total: number;
  percentage: number | null;
}

const STATUSES = [
  { key: "present", label: "Present", cls: "bg-green-600" },
  { key: "absent", label: "Absent", cls: "bg-red-600" },
  { key: "late", label: "Late", cls: "bg-amber-500" },
  { key: "excused", label: "Excused", cls: "bg-slate-500" },
];

const today = () => new Date().toISOString().slice(0, 10);

export default function AttendancePanel() {
  const [mode, setMode] = useState<"mark" | "summary">("mark");
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [batchId, setBatchId] = useState<number | "">("");
  const [date, setDate] = useState(today());
  const [periodNumber, setPeriodNumber] = useState(0);

  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const [fromDate, setFromDate] = useState(() => today().slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today());
  const [summary, setSummary] = useState<SummaryRow[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const list = await api.attendance.classes();
        setClasses(list);
        if (list.length) setBatchId(list[0].batch_id);
      } catch (e: any) {
        setErr(e?.response?.data?.error || "Couldn't load your classes.");
      }
    })();
  }, []);

  const loadRoster = async () => {
    if (batchId === "") return;
    try {
      setLoading(true);
      setErr("");
      setMsg("");
      const data = await api.attendance.roster({
        batch_id: batchId as number,
        date,
        period_number: periodNumber,
      });
      setRoster(data.students);
      if (data.already_marked) setMsg("Attendance already recorded for this day — you can update it below.");
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't load the class roster.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mode === "mark" && batchId !== "") loadRoster();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId, date, periodNumber, mode]);

  const setStatus = (studentId: number, status: string) => {
    setRoster((rows) => rows.map((r) => (r.student_id === studentId ? { ...r, status } : r)));
  };

  const markAll = (status: string) => {
    setRoster((rows) => rows.map((r) => ({ ...r, status })));
  };

  const counts = useMemo(() => {
    const c: Record<string, number> = { present: 0, absent: 0, late: 0, excused: 0 };
    roster.forEach((r) => { c[r.status] = (c[r.status] || 0) + 1; });
    return c;
  }, [roster]);

  const save = async () => {
    if (batchId === "") return;
    try {
      setSaving(true);
      setErr("");
      const res = await api.attendance.mark({
        batch_id: batchId as number,
        date,
        period_number: periodNumber,
        records: roster.map((r) => ({ student_id: r.student_id, status: r.status, remarks: r.remarks || undefined })),
      });
      setMsg(`Saved ${res.saved} record(s): ${res.summary.present} present, ${res.summary.absent} absent, ${res.summary.late} late, ${res.summary.excused} excused.`);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't save attendance.");
    } finally {
      setSaving(false);
    }
  };

  const loadSummary = async () => {
    if (batchId === "") return;
    try {
      setLoading(true);
      setErr("");
      const data = await api.attendance.summary({
        batch_id: batchId as number,
        from: fromDate,
        to: toDate,
        period_number: 0,
      });
      setSummary(data.students);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't load the summary.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mode === "summary" && batchId !== "") loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, batchId, fromDate, toDate]);

  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        <button
          onClick={() => { setMode("mark"); setMsg(""); setErr(""); }}
          className={`px-4 py-2 rounded-lg font-medium ${mode === "mark" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}
        >
          ✍️ Mark Attendance
        </button>
        <button
          onClick={() => { setMode("summary"); setMsg(""); setErr(""); }}
          className={`px-4 py-2 rounded-lg font-medium ${mode === "summary" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}
        >
          📈 Summary
        </button>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end bg-slate-50 border border-slate-200 rounded-lg p-4">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Class</label>
          <select
            value={batchId}
            onChange={(e) => setBatchId(e.target.value ? Number(e.target.value) : "")}
            className="border rounded px-3 py-2 bg-white min-w-[10rem]"
          >
            {classes.length === 0 && <option value="">No classes</option>}
            {classes.map((c) => (
              <option key={c.batch_id} value={c.batch_id}>{c.label} ({c.student_count})</option>
            ))}
          </select>
        </div>

        {mode === "mark" ? (
          <>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Date</label>
              <input type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)}
                     className="border rounded px-3 py-2 bg-white" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Type</label>
              <select value={periodNumber} onChange={(e) => setPeriodNumber(Number(e.target.value))}
                      className="border rounded px-3 py-2 bg-white">
                <option value={0}>Whole day</option>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((p) => <option key={p} value={p}>Period {p}</option>)}
              </select>
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">From</label>
              <input type="date" value={fromDate} max={toDate} onChange={(e) => setFromDate(e.target.value)}
                     className="border rounded px-3 py-2 bg-white" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">To</label>
              <input type="date" value={toDate} max={today()} onChange={(e) => setToDate(e.target.value)}
                     className="border rounded px-3 py-2 bg-white" />
            </div>
          </>
        )}
      </div>

      {msg && <div className="bg-green-50 border border-green-300 text-green-800 px-4 py-2 rounded-lg text-sm">{msg}</div>}
      {err && <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm">{err}</div>}

      {loading && <p className="text-slate-500 text-sm">⏳ Loading…</p>}

      {/* MARK MODE */}
      {mode === "mark" && !loading && (
        <>
          {roster.length === 0 ? (
            <p className="text-slate-500 text-sm">No students found for this class.</p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <span className="text-slate-600">Quick set:</span>
                {STATUSES.map((s) => (
                  <button key={s.key} onClick={() => markAll(s.key)}
                          className="px-3 py-1 rounded border border-slate-300 hover:bg-slate-100">
                    All {s.label}
                  </button>
                ))}
                <span className="ml-auto text-slate-600">
                  <span className="text-green-700 font-semibold">{counts.present}</span> present ·{" "}
                  <span className="text-red-700 font-semibold">{counts.absent}</span> absent ·{" "}
                  <span className="text-amber-600 font-semibold">{counts.late}</span> late ·{" "}
                  <span className="text-slate-700 font-semibold">{counts.excused}</span> excused
                </span>
              </div>

              <div className="border border-slate-200 rounded-lg divide-y">
                {roster.map((r) => (
                  <div key={r.student_id} className="flex items-center gap-3 px-3 py-2">
                    <span className="w-8 text-slate-400 text-sm">{r.roll_no ?? "—"}</span>
                    <span className="flex-1 font-medium text-slate-800">{r.name}</span>
                    <div className="flex gap-1">
                      {STATUSES.map((s) => (
                        <button
                          key={s.key}
                          onClick={() => setStatus(r.student_id, s.key)}
                          className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                            r.status === s.key ? `${s.cls} text-white` : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                          }`}
                        >
                          {s.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <button onClick={save} disabled={saving}
                      className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-bold py-2.5 px-6 rounded-lg">
                {saving ? "Saving…" : "Save Attendance"}
              </button>
            </>
          )}
        </>
      )}

      {/* SUMMARY MODE */}
      {mode === "summary" && !loading && (
        <div className="overflow-x-auto">
          {summary.length === 0 ? (
            <p className="text-slate-500 text-sm">No data for this range.</p>
          ) : (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-100 text-left">
                  <th className="border px-2 py-2 w-12">Roll</th>
                  <th className="border px-2 py-2">Student</th>
                  <th className="border px-2 py-2 text-center">Present</th>
                  <th className="border px-2 py-2 text-center">Absent</th>
                  <th className="border px-2 py-2 text-center">Late</th>
                  <th className="border px-2 py-2 text-center">Excused</th>
                  <th className="border px-2 py-2 text-center">%</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((r) => (
                  <tr key={r.student_id}>
                    <td className="border px-2 py-1.5 text-slate-400">{r.roll_no ?? "—"}</td>
                    <td className="border px-2 py-1.5 font-medium text-slate-800">{r.name}</td>
                    <td className="border px-2 py-1.5 text-center text-green-700">{r.present}</td>
                    <td className="border px-2 py-1.5 text-center text-red-700">{r.absent}</td>
                    <td className="border px-2 py-1.5 text-center text-amber-600">{r.late}</td>
                    <td className="border px-2 py-1.5 text-center text-slate-600">{r.excused}</td>
                    <td className={`border px-2 py-1.5 text-center font-semibold ${
                      r.percentage === null ? "text-slate-400"
                        : r.percentage < 75 ? "text-red-600" : "text-green-700"
                    }`}>
                      {r.percentage === null ? "—" : `${r.percentage}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
