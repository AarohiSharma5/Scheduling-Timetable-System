import React, { useState, useEffect } from "react";
import { api } from "../api";
import TeacherPreferenceEditor from "./TeacherPreferenceEditor";

interface UnavailableSlot {
  day: string;
  period: number;
}

interface TeachingAssignment {
  subject_id: number;
  batch_ids: number[];
}

interface ChargeAssignment {
  charge_id: number | null;
  name: string;
  hours_per_week: number;
}

interface Teacher {
  id: number;
  name: string;
  email: string;
  subject_ids: number[];
  assigned_batch_ids: number[];
  teaching_assignments: TeachingAssignment[];
  charges: ChargeAssignment[];
  charge_hours: number;
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

interface ChargeType {
  id: number;
  name: string;
  default_hours_per_week: number;
}

const emptyForm = {
  name: "",
  email: "",
  teaching_assignments: [] as TeachingAssignment[],
  charges: [] as ChargeAssignment[],
  unavailable_slots: [] as UnavailableSlot[],
  is_class_teacher: false,
};

export default function TeacherManagement() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [chargeTypes, setChargeTypes] = useState<ChargeType[]>([]);
  const [target, setTarget] = useState<number>(40);
  const [ctHours, setCtHours] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [prefTeacher, setPrefTeacher] = useState<Teacher | null>(null);

  const [formData, setFormData] = useState({ ...emptyForm });

  // Builders
  const [unavailDay, setUnavailDay] = useState("Monday");
  const [unavailPeriod, setUnavailPeriod] = useState(1);
  const [addSubjectId, setAddSubjectId] = useState<number | "">("");
  const [addChargeId, setAddChargeId] = useState<number | "">("");
  const [customTask, setCustomTask] = useState("");
  const [customHours, setCustomHours] = useState(2);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [teachersRes, subjectsRes, batchesRes, chargesRes, configRes] = await Promise.all([
        api.admin.teachers.list(),
        api.admin.subjects.list(),
        api.admin.batches.list(),
        api.admin.charges.list(),
        api.admin.config.get(),
      ]);
      setTeachers(Array.isArray(teachersRes) ? teachersRes : teachersRes.data || []);
      setSubjects(Array.isArray(subjectsRes) ? subjectsRes : subjectsRes.data || []);
      setBatches(Array.isArray(batchesRes) ? batchesRes : batchesRes.data || []);
      setChargeTypes(Array.isArray(chargesRes) ? chargesRes : chargesRes.data || []);
      if (configRes?.target_contact_periods_per_week) setTarget(configRes.target_contact_periods_per_week);
      setCtHours(configRes?.class_teacher_hours_per_week || 0);
    } catch (err) {
      setError("Failed to load data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const subjectName = (id: number) => subjects.find((s) => s.id === id)?.name || `#${id}`;
  const batchLabel = (id: number) => {
    const b = batches.find((x) => x.id === id);
    return b ? `${b.grade}-${b.section}` : `#${id}`;
  };

  // --- teaching assignments helpers ---
  const addSubjectRow = () => {
    if (addSubjectId === "") return;
    if (formData.teaching_assignments.some((a) => a.subject_id === addSubjectId)) return;
    setFormData({
      ...formData,
      teaching_assignments: [...formData.teaching_assignments, { subject_id: Number(addSubjectId), batch_ids: [] }],
    });
    setAddSubjectId("");
  };

  const removeSubjectRow = (subjectId: number) => {
    setFormData({
      ...formData,
      teaching_assignments: formData.teaching_assignments.filter((a) => a.subject_id !== subjectId),
    });
  };

  const setRowBatches = (subjectId: number, batchIds: number[]) => {
    setFormData({
      ...formData,
      teaching_assignments: formData.teaching_assignments.map((a) =>
        a.subject_id === subjectId ? { ...a, batch_ids: batchIds } : a
      ),
    });
  };

  // --- charges helpers ---
  const addCharge = () => {
    if (addChargeId === "") return;
    const ct = chargeTypes.find((c) => c.id === addChargeId);
    if (!ct) return;
    if (formData.charges.some((c) => c.charge_id === ct.id)) return;
    setFormData({
      ...formData,
      charges: [...formData.charges, { charge_id: ct.id, name: ct.name, hours_per_week: ct.default_hours_per_week }],
    });
    setAddChargeId("");
  };

  const addCustomCharge = () => {
    const name = customTask.trim();
    if (!name) return;
    if (formData.charges.some((c) => c.name.toLowerCase() === name.toLowerCase())) return;
    setFormData({
      ...formData,
      charges: [...formData.charges, { charge_id: null, name, hours_per_week: Math.max(0, customHours) }],
    });
    setCustomTask("");
    setCustomHours(2);
  };

  const setChargeHours = (idx: number, hours: number) => {
    setFormData({
      ...formData,
      charges: formData.charges.map((c, i) => (i === idx ? { ...c, hours_per_week: hours } : c)),
    });
  };

  const removeCharge = (idx: number) => {
    setFormData({ ...formData, charges: formData.charges.filter((_, i) => i !== idx) });
  };

  const chargeHours = formData.charges.reduce((sum, c) => sum + (Number(c.hours_per_week) || 0), 0);
  const classTeacherHours = formData.is_class_teacher ? ctHours : 0;
  const teachingCapacity = Math.max(0, target - chargeHours - classTeacherHours);

  // --- unavailable helpers ---
  const addUnavailable = () => {
    if (formData.unavailable_slots.some((s) => s.day === unavailDay && s.period === unavailPeriod)) return;
    setFormData({ ...formData, unavailable_slots: [...formData.unavailable_slots, { day: unavailDay, period: unavailPeriod }] });
  };
  const removeUnavailable = (idx: number) => {
    setFormData({ ...formData, unavailable_slots: formData.unavailable_slots.filter((_, i) => i !== idx) });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        name: formData.name,
        email: formData.email,
        teaching_assignments: formData.teaching_assignments,
        charges: formData.charges,
        unavailable_slots: formData.unavailable_slots,
        is_class_teacher: formData.is_class_teacher,
      };
      if (editingId) {
        await api.admin.teachers.update(editingId, payload);
      } else {
        await api.admin.teachers.create(payload);
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
    // Derive teaching_assignments; fall back to flat lists for legacy records.
    let assignments = teacher.teaching_assignments || [];
    if ((!assignments || assignments.length === 0) && (teacher.subject_ids || []).length) {
      assignments = teacher.subject_ids.map((sid) => ({ subject_id: sid, batch_ids: teacher.assigned_batch_ids || [] }));
    }
    setFormData({
      name: teacher.name,
      email: teacher.email,
      teaching_assignments: assignments.map((a) => ({ subject_id: a.subject_id, batch_ids: a.batch_ids || [] })),
      charges: (teacher.charges || []).map((c) => ({ ...c })),
      unavailable_slots: teacher.unavailable_slots || [],
      is_class_teacher: teacher.is_class_teacher,
    });
    setEditingId(teacher.id);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({ ...emptyForm });
    setEditingId(null);
    setShowForm(false);
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-900">Teachers</h2>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            + Add Teacher
          </button>
        )}
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <input type="text" placeholder="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="border rounded px-3 py-2" required />
            <input type="email" placeholder="Email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} className="border rounded px-3 py-2" required />
          </div>

          {/* Subjects → classes */}
          <div className="border-t pt-4">
            <label className="block text-sm font-medium mb-2">Subjects &amp; the classes they teach</label>
            <div className="flex items-end gap-2 mb-3">
              <select value={addSubjectId} onChange={(e) => setAddSubjectId(e.target.value === "" ? "" : Number(e.target.value))} className="border rounded px-3 py-2">
                <option value="">Select a subject…</option>
                {subjects.filter((s) => !formData.teaching_assignments.some((a) => a.subject_id === s.id)).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <button type="button" onClick={addSubjectRow} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">+ Add subject</button>
            </div>

            <div className="space-y-3">
              {formData.teaching_assignments.length === 0 && (
                <span className="text-sm text-slate-400">No subjects yet. Add a subject, then pick its classes.</span>
              )}
              {formData.teaching_assignments.map((a) => (
                <div key={a.subject_id} className="border rounded p-3 bg-slate-50">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-slate-800">{subjectName(a.subject_id)}</span>
                    <button type="button" onClick={() => removeSubjectRow(a.subject_id)} className="text-red-600 hover:underline text-sm">Remove</button>
                  </div>
                  <label className="block text-xs text-slate-500 mb-1">Classes for {subjectName(a.subject_id)}</label>
                  <select
                    multiple
                    value={a.batch_ids.map(String)}
                    onChange={(e) => setRowBatches(a.subject_id, Array.from(e.target.selectedOptions, (o) => Number(o.value)))}
                    className="border rounded px-3 py-2 w-full h-24"
                  >
                    {batches.map((b) => (
                      <option key={b.id} value={b.id}>Grade {b.grade} - {b.section}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          {/* Charges */}
          <div className="border-t pt-4">
            <label className="block text-sm font-medium mb-2">Charges / duties</label>
            <div className="flex items-end gap-2 mb-3">
              <select value={addChargeId} onChange={(e) => setAddChargeId(e.target.value === "" ? "" : Number(e.target.value))} className="border rounded px-3 py-2">
                <option value="">Select a charge…</option>
                {chargeTypes.filter((c) => !formData.charges.some((x) => x.charge_id === c.id)).map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.default_hours_per_week}h)</option>
                ))}
              </select>
              <button type="button" onClick={addCharge} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">+ Add from catalog</button>
            </div>
            {/* Ad-hoc: type any task + its weekly hours, no catalog entry needed */}
            <div className="flex flex-wrap items-end gap-2 mb-3">
              <input
                type="text"
                value={customTask}
                onChange={(e) => setCustomTask(e.target.value)}
                placeholder="Or type a task (e.g. Library duty)"
                className="border rounded px-3 py-2 w-64"
              />
              <input type="number" min={0} max={40} value={customHours} onChange={(e) => setCustomHours(Number(e.target.value))} className="border rounded px-3 py-2 w-24" />
              <span className="text-xs text-slate-500 mb-2">hrs/week</span>
              <button type="button" onClick={addCustomCharge} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">+ Add task</button>
            </div>
            <div className="space-y-2">
              {formData.charges.map((c, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <span className="text-sm text-slate-800 w-48">{c.name}{c.charge_id == null && <span className="text-xs text-slate-400"> (custom)</span>}</span>
                  <input type="number" min={0} max={40} value={c.hours_per_week} onChange={(e) => setChargeHours(idx, Number(e.target.value))} className="border rounded px-2 py-1 w-24" />
                  <span className="text-xs text-slate-500">hrs/week</span>
                  <button type="button" onClick={() => removeCharge(idx)} className="text-red-600 hover:underline text-sm">Remove</button>
                </div>
              ))}
            </div>
            <div className="mt-3 bg-blue-50 border border-blue-200 rounded p-3 text-sm text-slate-700">
              Contact target: <strong>{target}</strong> periods/week &nbsp;•&nbsp; Charges: <strong>{chargeHours}</strong> hrs
              {formData.is_class_teacher && <> &nbsp;•&nbsp; Class teacher: <strong>{ctHours}</strong> hrs</>}
              &nbsp;•&nbsp; Teaching capacity: <strong>{teachingCapacity}</strong> periods/week
              <div className="text-xs text-slate-500 mt-1">
                Teaching capacity is computed automatically so every teacher carries the same total load.
                {ctHours === 0 && " (Set class-teacher hours under Configuration → Teacher Workload.)"}
              </div>
            </div>
            <label className="flex items-center mt-3">
              <input type="checkbox" checked={formData.is_class_teacher} onChange={(e) => setFormData({ ...formData, is_class_teacher: e.target.checked })} className="mr-2" />
              Class Teacher
            </label>
          </div>

          {/* Availability */}
          <div className="border-t pt-4">
            <label className="block text-sm font-medium mb-2">Unavailable periods (availability)</label>
            <div className="flex flex-wrap items-end gap-2 mb-3">
              <select value={unavailDay} onChange={(e) => setUnavailDay(e.target.value)} className="border rounded px-3 py-2">
                {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <input type="number" min="1" max="12" value={unavailPeriod} onChange={(e) => setUnavailPeriod(Number(e.target.value))} className="border rounded px-3 py-2 w-24" placeholder="Period" />
              <button type="button" onClick={addUnavailable} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">+ Block period</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.unavailable_slots.length === 0 && <span className="text-sm text-slate-400">Available all periods.</span>}
              {formData.unavailable_slots.map((s, idx) => (
                <span key={`${s.day}-${s.period}`} className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-sm px-2 py-1 rounded">
                  {s.day} P{s.period}
                  <button type="button" onClick={() => removeUnavailable(idx)} className="text-amber-900 hover:text-red-600 font-bold">×</button>
                </span>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <button type="submit" className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">{editingId ? "Update" : "Create"}</button>
            <button type="button" onClick={resetForm} className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded">Cancel</button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Teaches</th>
              <th className="px-4 py-2 text-left">Charges</th>
              <th className="px-4 py-2 text-left">Teaching cap.</th>
              <th className="px-4 py-2 text-left">Unavailable</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {teachers.map((teacher) => {
              const assignments = (teacher.teaching_assignments && teacher.teaching_assignments.length)
                ? teacher.teaching_assignments
                : (teacher.subject_ids || []).map((sid) => ({ subject_id: sid, batch_ids: teacher.assigned_batch_ids || [] }));
              return (
                <tr key={teacher.id} className="border-b hover:bg-slate-50 align-top">
                  <td className="px-4 py-2">
                    <div>{teacher.name}</div>
                    <div className="text-xs text-slate-400">{teacher.email}</div>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {assignments.length === 0 ? <span className="text-slate-400">—</span> : assignments.map((a) => (
                      <div key={a.subject_id}>
                        <span className="font-medium">{subjectName(a.subject_id)}</span>
                        <span className="text-slate-500"> → {a.batch_ids.map(batchLabel).join(", ") || "—"}</span>
                      </div>
                    ))}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {(teacher.charges && teacher.charges.length > 0)
                      ? teacher.charges.map((c) => `${c.name} (${c.hours_per_week}h)`).join(", ")
                      : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-2 text-sm">{teacher.max_periods_per_week}/wk</td>
                  <td className="px-4 py-2 text-sm">
                    {(teacher.unavailable_slots && teacher.unavailable_slots.length > 0)
                      ? teacher.unavailable_slots.map((s) => `${s.day.slice(0, 3)} P${s.period}`).join(", ")
                      : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-2 space-x-2 whitespace-nowrap">
                    <button onClick={() => handleEdit(teacher)} className="text-blue-600 hover:underline text-sm">Edit</button>
                    <button onClick={() => setPrefTeacher(teacher)} className="text-purple-600 hover:underline text-sm">Preferences</button>
                    <button onClick={() => handleDelete(teacher.id)} className="text-red-600 hover:underline text-sm">Delete</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {prefTeacher && (
        <TeacherPreferenceEditor
          teacherId={prefTeacher.id}
          teacherName={prefTeacher.name}
          subjects={subjects}
          batches={batches}
          onClose={() => setPrefTeacher(null)}
        />
      )}
    </div>
  );
}
