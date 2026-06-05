import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Assignment {
  id: number;
  title: string;
  subject: string | null;
  description: string | null;
  due_date: string | null;
  my_status?: string;
  my_grade?: string | null;
  my_feedback?: string | null;
}

const statusBadge = (s: string) => {
  const map: Record<string, string> = {
    pending: "bg-slate-100 text-slate-600",
    submitted: "bg-blue-100 text-blue-800",
    graded: "bg-emerald-100 text-emerald-800",
  };
  return map[s] || "bg-slate-100 text-slate-700";
};

export default function StudentAssignmentsView({ studentId }: { studentId: number }) {
  const [items, setItems] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const res = await api.assignments.student(studentId);
        if (active) setItems(res.assignments || []);
      } catch (e: any) {
        if (active) setErr(e?.response?.data?.error || "Could not load homework.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [studentId]);

  if (loading) return <div className="text-sm text-slate-500">Loading homework…</div>;
  if (err) return <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>;
  if (!items.length) return <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">No homework on record.</div>;

  return (
    <div className="space-y-3">
      {items.map((a) => (
        <div key={a.id} className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-semibold text-slate-800">{a.title}</div>
              <div className="mt-0.5 text-xs text-slate-500">
                {a.subject || "General"}{a.due_date ? ` · Due ${a.due_date}` : ""}
              </div>
              {a.description && <p className="mt-2 text-sm text-slate-600">{a.description}</p>}
              {a.my_feedback && <p className="mt-1 text-xs text-emerald-700">Feedback: {a.my_feedback}</p>}
            </div>
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${statusBadge(a.my_status || "pending")}`}>
              {a.my_grade ? `Grade: ${a.my_grade}` : a.my_status || "pending"}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
