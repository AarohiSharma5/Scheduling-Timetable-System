import React, { useState, useEffect } from "react";
import { api } from "../api";

interface PinnedSlot {
  id: number;
  batch_id: number;
  subject_id: number;
  teacher_id: number | null;
  day: string;
  period_number: number;
}

interface Batch {
  id: number;
  grade: string;
  section: string;
}

interface Subject {
  id: number;
  name: string;
}

interface Teacher {
  id: number;
  name: string;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function PinnedSlotsManager() {
  const [pins, setPins] = useState<PinnedSlot[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    batch_id: "",
    subject_id: "",
    teacher_id: "",
    day: "Monday",
    period_number: 1,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [pinsRes, batchesRes, subjectsRes, teachersRes] = await Promise.all([
        api.admin.pinnedSlots.list(),
        api.admin.batches.list(),
        api.admin.subjects.list(),
        api.admin.teachers.list(),
      ]);
      setPins(pinsRes || []);
      setBatches(Array.isArray(batchesRes) ? batchesRes : batchesRes.data || []);
      setSubjects(Array.isArray(subjectsRes) ? subjectsRes : subjectsRes.data || []);
      setTeachers(Array.isArray(teachersRes) ? teachersRes : teachersRes.data || []);
    } catch (err) {
      setError("Failed to load fixed periods");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.admin.pinnedSlots.create({
        batch_id: Number(form.batch_id),
        subject_id: Number(form.subject_id),
        teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
        day: form.day,
        period_number: Number(form.period_number),
      });
      setForm({ batch_id: "", subject_id: "", teacher_id: "", day: "Monday", period_number: 1 });
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to add fixed period");
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Remove this fixed period?")) return;
    try {
      await api.admin.pinnedSlots.delete(id);
      await loadData();
    } catch (err) {
      setError("Failed to remove fixed period");
      console.error(err);
    }
  };

  const batchLabel = (id: number) => {
    const b = batches.find((x) => x.id === id);
    return b ? `Grade ${b.grade} - ${b.section}` : `Batch ${id}`;
  };
  const subjectLabel = (id: number) => subjects.find((x) => x.id === id)?.name || `Subject ${id}`;
  const teacherLabel = (id: number | null) =>
    id ? teachers.find((x) => x.id === id)?.name || `Teacher ${id}` : "Auto-assigned";

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Fixed / Pinned Periods</h2>
        <p className="text-sm text-slate-500 mt-1">
          Lock specific periods (e.g. a fixed lab, assembly or library slot). The generator
          places these first and schedules everything else around them.
        </p>
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">Class</label>
            <select value={form.batch_id} onChange={(e) => setForm({ ...form, batch_id: e.target.value })} className="border rounded px-3 py-2 w-full" required>
              <option value="">Select…</option>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>Grade {b.grade} - {b.section}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subject</label>
            <select value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })} className="border rounded px-3 py-2 w-full" required>
              <option value="">Select…</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Teacher (optional)</label>
            <select value={form.teacher_id} onChange={(e) => setForm({ ...form, teacher_id: e.target.value })} className="border rounded px-3 py-2 w-full">
              <option value="">Auto</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Day</label>
            <select value={form.day} onChange={(e) => setForm({ ...form, day: e.target.value })} className="border rounded px-3 py-2 w-full">
              {DAYS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Period</label>
            <input type="number" min="1" max="12" value={form.period_number} onChange={(e) => setForm({ ...form, period_number: Number(e.target.value) })} className="border rounded px-3 py-2 w-full" required />
          </div>
        </div>
        <button type="submit" className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
          + Pin period
        </button>
      </form>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Class</th>
              <th className="px-4 py-2 text-left">Subject</th>
              <th className="px-4 py-2 text-left">Teacher</th>
              <th className="px-4 py-2 text-left">When</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pins.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-400">No fixed periods yet.</td>
              </tr>
            )}
            {pins.map((p) => (
              <tr key={p.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-2">{batchLabel(p.batch_id)}</td>
                <td className="px-4 py-2">{subjectLabel(p.subject_id)}</td>
                <td className="px-4 py-2 text-sm">{teacherLabel(p.teacher_id)}</td>
                <td className="px-4 py-2">{p.day} · P{p.period_number}</td>
                <td className="px-4 py-2">
                  <button onClick={() => handleDelete(p.id)} className="text-red-600 hover:underline text-sm">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
