import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

interface Assignment {
  id: number;
  batch_id: number;
  subject_id: number | null;
  subject: string | null;
  batch_label: string | null;
  title: string;
  description: string | null;
  author_name: string | null;
  due_date: string | null;
  my_status?: string;
  my_grade?: string | null;
}

interface ClassOption {
  batch_id: number;
  label: string;
  subject_ids: number[];
}
interface SubjectOption {
  id: number;
  name: string;
}

interface SubmissionRow {
  student_id: number;
  name: string;
  roll_no: number | null;
  status: string;
  note: string | null;
  grade: string | null;
  feedback: string | null;
  submitted_at: string | null;
}

const statusBadge = (s: string) => {
  const map: Record<string, string> = {
    pending: "bg-slate-100 text-slate-600",
    submitted: "bg-blue-100 text-blue-800",
    graded: "bg-emerald-100 text-emerald-800",
  };
  return map[s] || "bg-slate-100 text-slate-700";
};

export default function AssignmentsPanel() {
  const role = useAuthStore((s) => s.user?.role);
  const isStaff = role === "admin" || role === "principal" || role === "teacher";
  const isStudent = role === "student";

  const [items, setItems] = useState<Assignment[]>([]);
  const [classes, setClasses] = useState<ClassOption[]>([]);
  const [subjects, setSubjects] = useState<SubjectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [showForm, setShowForm] = useState(false);

  // create form
  const [title, setTitle] = useState("");
  const [batchId, setBatchId] = useState<number | "">("");
  const [subjectId, setSubjectId] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);

  // submissions drawer (staff)
  const [openSubs, setOpenSubs] = useState<number | null>(null);
  const [subs, setSubs] = useState<SubmissionRow[]>([]);

  const flash = (m: string) => {
    setMsg(m);
    setTimeout(() => setMsg(""), 2500);
  };

  const load = async () => {
    try {
      setLoading(true);
      setErr("");
      const list = await api.assignments.list();
      setItems(list);
      if (isStaff) {
        const meta = await api.assignments.meta();
        setClasses(meta.classes);
        setSubjects(meta.subjects);
      }
    } catch {
      setErr("Could not load homework.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !batchId) return;
    try {
      setSaving(true);
      await api.assignments.create({
        title: title.trim(),
        batch_id: Number(batchId),
        subject_id: subjectId ? Number(subjectId) : null,
        description: description.trim() || undefined,
        due_date: dueDate || undefined,
      });
      setTitle(""); setBatchId(""); setSubjectId(""); setDescription(""); setDueDate("");
      setShowForm(false);
      flash("Homework posted.");
      load();
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Could not post homework.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this assignment?")) return;
    await api.assignments.remove(id);
    flash("Deleted.");
    load();
  };

  const submit = async (id: number) => {
    const note = window.prompt("Add a note (optional):") || "";
    await api.assignments.submit(id, { note });
    flash("Marked as submitted.");
    load();
  };

  const openSubmissions = async (id: number) => {
    if (openSubs === id) {
      setOpenSubs(null);
      return;
    }
    const res = await api.assignments.submissions(id);
    setSubs(res.students);
    setOpenSubs(id);
  };

  const grade = async (aid: number, studentId: number, gradeVal: string, feedback: string) => {
    await api.assignments.grade(aid, studentId, { grade: gradeVal, feedback });
    flash("Saved.");
    const res = await api.assignments.submissions(aid);
    setSubs(res.students);
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Homework</h2>
        {isStaff && (
          <button onClick={() => setShowForm((v) => !v)} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">
            {showForm ? "Close" : "+ New homework"}
          </button>
        )}
      </div>

      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}
      {msg && <div className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{msg}</div>}

      {isStaff && showForm && (
        <form onSubmit={create} className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm" value={batchId} onChange={(e) => setBatchId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Select class…</option>
              {classes.map((c) => <option key={c.batch_id} value={c.batch_id}>{c.label}</option>)}
            </select>
            <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm" value={subjectId} onChange={(e) => setSubjectId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Subject (optional)</option>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>
          <textarea className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" rows={3} placeholder="Details (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Posting…" : "Post"}</button>
        </form>
      )}

      {loading && <div className="text-sm text-slate-500">Loading…</div>}

      <div className="space-y-3">
        {items.map((a) => (
          <div key={a.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-semibold text-slate-800">{a.title}</div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {a.batch_label}{a.subject ? ` · ${a.subject}` : ""}
                  {a.due_date ? ` · Due ${a.due_date}` : ""}
                  {a.author_name ? ` · ${a.author_name}` : ""}
                </div>
                {a.description && <p className="mt-2 text-sm text-slate-600">{a.description}</p>}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {isStudent && (
                  <>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusBadge(a.my_status || "pending")}`}>
                      {a.my_grade ? `Grade: ${a.my_grade}` : a.my_status || "pending"}
                    </span>
                    {a.my_status !== "graded" && (
                      <button onClick={() => submit(a.id)} className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white">
                        {a.my_status === "submitted" ? "Re-submit" : "Mark submitted"}
                      </button>
                    )}
                  </>
                )}
                {isStaff && (
                  <>
                    <button onClick={() => openSubmissions(a.id)} className="rounded-md bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                      {openSubs === a.id ? "Hide" : "Submissions"}
                    </button>
                    <button onClick={() => remove(a.id)} className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Delete</button>
                  </>
                )}
              </div>
            </div>

            {isStaff && openSubs === a.id && (
              <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500">
                    <tr><th className="px-3 py-2">Roll</th><th className="px-3 py-2">Student</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Grade</th><th className="px-3 py-2">Feedback</th></tr>
                  </thead>
                  <tbody>
                    {subs.map((r) => (
                      <SubmissionEditor key={r.student_id} row={r} onSave={(g, f) => grade(a.id, r.student_id, g, f)} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
        {!loading && !items.length && <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">No homework yet.</div>}
      </div>
    </div>
  );
}

function SubmissionEditor({ row, onSave }: { row: SubmissionRow; onSave: (g: string, f: string) => void }) {
  const [g, setG] = useState(row.grade || "");
  const [f, setF] = useState(row.feedback || "");
  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2">{row.roll_no ?? "—"}</td>
      <td className="px-3 py-2 font-medium text-slate-800">{row.name}</td>
      <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusBadge(row.status)}`}>{row.status}</span></td>
      <td className="px-3 py-2"><input className="w-16 rounded border border-slate-300 px-2 py-1 text-xs" value={g} onChange={(e) => setG(e.target.value)} placeholder="A" /></td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <input className="w-40 rounded border border-slate-300 px-2 py-1 text-xs" value={f} onChange={(e) => setF(e.target.value)} placeholder="Feedback" />
          <button onClick={() => onSave(g, f)} className="rounded bg-indigo-600 px-2 py-1 text-xs font-semibold text-white">Save</button>
        </div>
      </td>
    </tr>
  );
}
