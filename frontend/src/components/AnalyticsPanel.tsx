import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Overview {
  students: { total: number; teachers: number; by_grade: Record<string, number> };
  attendance: { rate: number | null; present: number; absent: number; late: number; marks: number };
  fees: { billed: number; collected: number; outstanding: number; collection_rate: number | null };
  exams: { published: number; graded_marks: number; pass_rate: number | null };
  library: { books: number; issued: number; overdue: number };
  transport: { routes: number; students: number };
  inventory: { items: number; low_stock: number };
}

const money = (n: number) => "\u20b9" + (n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
const pct = (n: number | null) => (n == null ? "—" : `${n}%`);

function Card({ label, value, sub, accent = "text-slate-800" }: { label: string; value: React.ReactNode; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

export default function AnalyticsPanel() {
  const [data, setData] = useState<Overview | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.analytics.overview().then(setData).catch(() => setErr("Could not load analytics.")).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-sm text-slate-500">Loading analytics…</div>;
  if (err) return <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-800">School Analytics</h2>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Active students" value={data.students.total} sub={`${data.students.teachers} teachers`} />
        <Card label="Attendance rate" value={pct(data.attendance.rate)} sub={`${data.attendance.marks} marks recorded`} accent="text-blue-600" />
        <Card label="Fees collected" value={money(data.fees.collected)} sub={`${pct(data.fees.collection_rate)} of ${money(data.fees.billed)}`} accent="text-emerald-600" />
        <Card label="Outstanding fees" value={money(data.fees.outstanding)} accent="text-rose-600" />
        <Card label="Exam pass rate" value={pct(data.exams.pass_rate)} sub={`${data.exams.published} published exams`} accent="text-violet-600" />
        <Card label="Library" value={`${data.library.issued} on loan`} sub={`${data.library.books} books · ${data.library.overdue} overdue`} />
        <Card label="Transport" value={`${data.transport.students} students`} sub={`${data.transport.routes} routes`} />
        <Card label="Inventory" value={`${data.inventory.items} items`} sub={`${data.inventory.low_stock} low on stock`} accent={data.inventory.low_stock ? "text-rose-600" : "text-slate-800"} />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-3 text-sm font-semibold text-slate-700">Students by grade</div>
        {Object.keys(data.students.by_grade).length === 0 ? (
          <div className="text-sm text-slate-400">No students yet.</div>
        ) : (
          <div className="space-y-2">
            {Object.entries(data.students.by_grade).map(([grade, count]) => {
              const max = Math.max(...Object.values(data.students.by_grade));
              return (
                <div key={grade} className="flex items-center gap-3">
                  <div className="w-20 text-sm text-slate-600">Grade {grade}</div>
                  <div className="h-4 flex-1 rounded bg-slate-100">
                    <div className="h-4 rounded bg-indigo-500" style={{ width: `${max ? (count / max) * 100 : 0}%` }} />
                  </div>
                  <div className="w-8 text-right text-sm font-medium text-slate-700">{count}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
