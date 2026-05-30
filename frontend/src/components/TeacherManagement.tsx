import React, { useState, useEffect } from "react";
import { api } from "../api";

interface UnavailableSlot {
  day: string;
  period: number;
}

interface Teacher {
  id: number;
  name: string;
  email: string;
  subject_ids: number[];
  assigned_batch_ids: number[];
  unavailable_slots: UnavailableSlot[];
  is_class_teacher: boolean;
  max_periods_per_week: number;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

interface Subject {
  id: number;
  name: string;
}

interface Batch {
  id: number;
  grade: string;
  section: string;
}

export default function TeacherManagement() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject_ids: [] as number[],
    assigned_batch_ids: [] as number[],
    unavailable_slots: [] as UnavailableSlot[],
    is_class_teacher: false,
    max_periods_per_week: 24,
  });

  // Builder controls for adding an unavailable slot.
  const [unavailDay, setUnavailDay] = useState("Monday");
  const [unavailPeriod, setUnavailPeriod] = useState(1);

  const addUnavailable = () => {
    const exists = formData.unavailable_slots.some(
      (s) => s.day === unavailDay && s.period === unavailPeriod
    );
    if (exists) return;
    setFormData({
      ...formData,
      unavailable_slots: [...formData.unavailable_slots, { day: unavailDay, period: unavailPeriod }],
    });
  };

  const removeUnavailable = (idx: number) => {
    setFormData({
      ...formData,
      unavailable_slots: formData.unavailable_slots.filter((_, i) => i !== idx),
    });
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [teachersRes, subjectsRes, batchesRes] = await Promise.all([
        api.admin.teachers.list(),
        api.admin.subjects.list(),
        api.admin.batches.list(),
      ]);
      setTeachers(Array.isArray(teachersRes) ? teachersRes : teachersRes.data || []);
      setSubjects(Array.isArray(subjectsRes) ? subjectsRes : subjectsRes.data || []);
      setBatches(Array.isArray(batchesRes) ? batchesRes : batchesRes.data || []);
    } catch (err) {
      setError("Failed to load data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.admin.teachers.update(editingId, formData);
      } else {
        await api.admin.teachers.create(formData);
      }
      await loadData();
      resetForm();
    } catch (err) {
      setError("Failed to save teacher");
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this teacher?")) return;
    try {
      await api.admin.teachers.delete(id);
      await loadData();
    } catch (err) {
      setError("Failed to delete teacher");
      console.error(err);
    }
  };

  const handleEdit = (teacher: Teacher) => {
    setFormData({
      name: teacher.name,
      email: teacher.email,
      subject_ids: teacher.subject_ids,
      assigned_batch_ids: teacher.assigned_batch_ids,
      unavailable_slots: teacher.unavailable_slots || [],
      is_class_teacher: teacher.is_class_teacher,
      max_periods_per_week: teacher.max_periods_per_week,
    });
    setEditingId(teacher.id);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      email: "",
      subject_ids: [],
      assigned_batch_ids: [],
      unavailable_slots: [],
      is_class_teacher: false,
      max_periods_per_week: 24,
    });
    setEditingId(null);
    setShowForm(false);
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-900">Teachers</h2>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            + Add Teacher
          </button>
        )}
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <input type="text" placeholder="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="border rounded px-3 py-2" required />
            <input type="email" placeholder="Email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} className="border rounded px-3 py-2" required />

            <div>
              <label className="block text-sm font-medium mb-1">Subjects</label>
              <select multiple value={formData.subject_ids.map(String)} onChange={(e) => setFormData({ ...formData, subject_ids: Array.from(e.target.selectedOptions, (opt) => Number(opt.value)) })} className="border rounded px-3 py-2 w-full">
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Classes</label>
              <select multiple value={formData.assigned_batch_ids.map(String)} onChange={(e) => setFormData({ ...formData, assigned_batch_ids: Array.from(e.target.selectedOptions, (opt) => Number(opt.value)) })} className="border rounded px-3 py-2 w-full">
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    Grade {b.grade} - Section {b.section}
                  </option>
                ))}
              </select>
            </div>

            <input type="number" placeholder="Max Periods/Week" value={formData.max_periods_per_week} onChange={(e) => setFormData({ ...formData, max_periods_per_week: Number(e.target.value) })} className="border rounded px-3 py-2" min="1" max="40" />

            <label className="flex items-center">
              <input type="checkbox" checked={formData.is_class_teacher} onChange={(e) => setFormData({ ...formData, is_class_teacher: e.target.checked })} className="mr-2" />
              Class Teacher
            </label>
          </div>

          {/* Availability: slots the teacher cannot be scheduled into */}
          <div className="border-t pt-4">
            <label className="block text-sm font-medium mb-2">Unavailable periods (availability)</label>
            <div className="flex flex-wrap items-end gap-2 mb-3">
              <select value={unavailDay} onChange={(e) => setUnavailDay(e.target.value)} className="border rounded px-3 py-2">
                {DAYS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <input type="number" min="1" max="12" value={unavailPeriod} onChange={(e) => setUnavailPeriod(Number(e.target.value))} className="border rounded px-3 py-2 w-24" placeholder="Period" />
              <button type="button" onClick={addUnavailable} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">
                + Block period
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.unavailable_slots.length === 0 && (
                <span className="text-sm text-slate-400">Available all periods.</span>
              )}
              {formData.unavailable_slots.map((s, idx) => (
                <span key={`${s.day}-${s.period}`} className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-sm px-2 py-1 rounded">
                  {s.day} P{s.period}
                  <button type="button" onClick={() => removeUnavailable(idx)} className="text-amber-900 hover:text-red-600 font-bold">×</button>
                </span>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <button type="submit" className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
              {editingId ? "Update" : "Create"}
            </button>
            <button type="button" onClick={resetForm} className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded">
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Email</th>
              <th className="px-4 py-2 text-left">Subjects</th>
              <th className="px-4 py-2 text-left">Classes</th>
              <th className="px-4 py-2 text-left">Unavailable</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {teachers.map((teacher) => (
              <tr key={teacher.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-2">{teacher.name}</td>
                <td className="px-4 py-2">{teacher.email}</td>
                <td className="px-4 py-2 text-sm">{subjects.filter((s) => teacher.subject_ids.includes(s.id)).map((s) => s.name).join(", ")}</td>
                <td className="px-4 py-2 text-sm">{batches.filter((b) => teacher.assigned_batch_ids.includes(b.id)).map((b) => `Grade ${b.grade} - ${b.section}`).join(", ")}</td>
                <td className="px-4 py-2 text-sm">
                  {(teacher.unavailable_slots && teacher.unavailable_slots.length > 0)
                    ? teacher.unavailable_slots.map((s) => `${s.day.slice(0, 3)} P${s.period}`).join(", ")
                    : <span className="text-slate-400">—</span>}
                </td>
                <td className="px-4 py-2 space-x-2">
                  <button onClick={() => handleEdit(teacher)} className="text-blue-600 hover:underline text-sm">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(teacher.id)} className="text-red-600 hover:underline text-sm">
                    Delete
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
