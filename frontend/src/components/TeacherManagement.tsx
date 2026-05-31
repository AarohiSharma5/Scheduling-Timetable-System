import React, { useState, useEffect, useRef } from "react";
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

interface SubjectGrade {
  subject_id: number;
  grades: string[];
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
  subject_grades: SubjectGrade[];
  takes_classes: boolean;
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
  subject_grades: [] as SubjectGrade[],
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
  const [autoMsg, setAutoMsg] = useState("");
  const [autoBusy, setAutoBusy] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  // Lock the background page scroll while the edit/add modal is open so the
  // focus stays on the dialog and the page behind doesn't drift.
  useEffect(() => {
    if (showForm) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = prev; };
    }
  }, [showForm]);

  // Move keyboard focus into the dialog when it opens (Add) or switches teacher (Edit).
  useEffect(() => {
    if (showForm && formRef.current) {
      const first = formRef.current.querySelector<HTMLInputElement>("input, select, textarea");
      first?.focus();
    }
  }, [showForm, editingId]);

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

  // Unique grade list (ordered: numeric grades first, then names like Nursery).
  const grades = Array.from(new Set(batches.map((b) => b.grade))).sort((a, b) => {
    const na = Number(a), nb = Number(b);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    if (!isNaN(na)) return -1;
    if (!isNaN(nb)) return 1;
    return a.localeCompare(b);
  });

  // --- capability helpers (subject + grades) ---
  const addSubjectRow = () => {
    if (addSubjectId === "") return;
    if (formData.subject_grades.some((a) => a.subject_id === addSubjectId)) return;
    setFormData({
      ...formData,
      subject_grades: [...formData.subject_grades, { subject_id: Number(addSubjectId), grades: [] }],
    });
    setAddSubjectId("");
  };

  const removeSubjectRow = (subjectId: number) => {
    setFormData({
      ...formData,
      subject_grades: formData.subject_grades.filter((a) => a.subject_id !== subjectId),
    });
  };

  const setRowGrades = (subjectId: number, gradeVals: string[]) => {
    setFormData({
      ...formData,
      subject_grades: formData.subject_grades.map((a) =>
        a.subject_id === subjectId ? { ...a, grades: gradeVals } : a
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
        subject_grades: formData.subject_grades,
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

  const handleAutoAssign = async () => {
    if (!window.confirm("Redistribute all sections fairly from teachers' subject + grade capability? This rewrites current section assignments.")) return;
    try {
      setAutoBusy(true);
      setAutoMsg("");
      const res = await api.admin.teachers.autoAssignSections();
      const uncovered = res.uncovered?.length || 0;
      let msg = `Assigned ${res.assigned} class-subjects across ${res.teacher_loads?.length || 0} teachers.`;
      if (res.over_capacity_assignments) msg += ` ${res.over_capacity_assignments} placed over soft capacity.`;
      if (uncovered) msg += ` ⚠️ ${uncovered} class-subject(s) have no capable teacher.`;
      setAutoMsg(msg);
      await loadData();
    } catch (err) {
      setAutoMsg("Auto-assign failed.");
      console.error(err);
    } finally {
      setAutoBusy(false);
    }
  };

  const handleEdit = (teacher: Teacher) => {
    // Prefer declared capability; fall back to deriving grades from current sections.
    let caps = teacher.subject_grades || [];
    if ((!caps || caps.length === 0) && (teacher.teaching_assignments || []).length) {
      caps = teacher.teaching_assignments.map((a) => ({
        subject_id: a.subject_id,
        grades: Array.from(new Set((a.batch_ids || []).map((bid) => {
          const b = batches.find((x) => x.id === bid);
          return b ? b.grade : "";
        }).filter(Boolean))),
      }));
    }
    setFormData({
      name: teacher.name,
      email: teacher.email,
      subject_grades: caps.map((a) => ({ subject_id: a.subject_id, grades: a.grades || [] })),
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
        <div className="flex gap-2">
          <button onClick={handleAutoAssign} disabled={autoBusy} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg">
            {autoBusy ? "Assigning…" : "⚖️ Auto-assign sections"}
          </button>
          {!showForm && (
            <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
              + Add Teacher
            </button>
          )}
        </div>
      </div>

      <p className="text-sm text-slate-500 -mt-2">
        Teachers declare the subjects and <strong>grades</strong> they can teach; "Auto-assign sections" then
        distributes the actual sections fairly so every class is covered and load is balanced.
      </p>

      {autoMsg && <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 px-4 py-3 rounded text-sm">{autoMsg}</div>}
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {showForm && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:p-6"
          onMouseDown={(e) => { if (e.target === e.currentTarget) resetForm(); }}
        >
          <form
            ref={formRef}
            onSubmit={handleSubmit}
            className="bg-white p-6 rounded-lg shadow-2xl space-y-5 w-full max-w-2xl my-8 max-h-[90vh] overflow-y-auto"
          >
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-slate-900">{editingId ? "Edit teacher" : "Add teacher"}</h3>
            <button type="button" onClick={resetForm} className="text-slate-400 hover:text-slate-700 text-2xl leading-none" aria-label="Close">×</button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <input type="text" placeholder="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="border rounded px-3 py-2" required />
            <input type="email" placeholder="Email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} className="border rounded px-3 py-2" required />
          </div>

          {/* Capability: subjects + grades they can teach */}
          <div className="border-t pt-4">
            <label className="block text-sm font-medium mb-1">Subjects &amp; grades they can teach</label>
            <p className="text-xs text-slate-500 mb-2">Pick the grades (e.g. 8, 9, 10). Exact sections are distributed fairly by "Auto-assign sections".</p>
            <div className="flex items-end gap-2 mb-3">
              <select value={addSubjectId} onChange={(e) => setAddSubjectId(e.target.value === "" ? "" : Number(e.target.value))} className="border rounded px-3 py-2">
                <option value="">Select a subject…</option>
                {subjects.filter((s) => !formData.subject_grades.some((a) => a.subject_id === s.id)).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <button type="button" onClick={addSubjectRow} className="bg-slate-700 hover:bg-slate-800 text-white px-3 py-2 rounded">+ Add subject</button>
            </div>

            <div className="space-y-3">
              {formData.subject_grades.length === 0 && (
                <span className="text-sm text-slate-400">No subjects yet. Add a subject, then pick the grades.</span>
              )}
              {formData.subject_grades.map((a) => (
                <div key={a.subject_id} className="border rounded p-3 bg-slate-50">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-slate-800">{subjectName(a.subject_id)}</span>
                    <button type="button" onClick={() => removeSubjectRow(a.subject_id)} className="text-red-600 hover:underline text-sm">Remove</button>
                  </div>
                  <label className="block text-xs text-slate-500 mb-1">Grades for {subjectName(a.subject_id)}</label>
                  <div className="flex flex-wrap gap-2">
                    {grades.map((g) => {
                      const on = a.grades.includes(g);
                      return (
                        <button
                          type="button"
                          key={g}
                          onClick={() => setRowGrades(a.subject_id, on ? a.grades.filter((x) => x !== g) : [...a.grades, g])}
                          className={`px-2 py-1 rounded text-sm border ${on ? "bg-blue-600 text-white border-blue-600" : "bg-white text-slate-700 border-slate-300"}`}
                        >
                          {g}
                        </button>
                      );
                    })}
                  </div>
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
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Can teach (subject → grades)</th>
              <th className="px-4 py-2 text-left">Assigned sections</th>
              <th className="px-4 py-2 text-left">Charges</th>
              <th className="px-4 py-2 text-left">Cap.</th>
              <th className="px-4 py-2 text-left">Unavailable</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {teachers.map((teacher) => {
              const assignments = teacher.teaching_assignments || [];
              const caps = teacher.subject_grades || [];
              return (
                <tr key={teacher.id} className="border-b hover:bg-slate-50 align-top">
                  <td className="px-4 py-2">
                    <div>{teacher.name}</div>
                    <div className="text-xs text-slate-400">{teacher.email}</div>
                    {!teacher.takes_classes && <span className="text-xs bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded">substitute</span>}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {caps.length === 0 ? <span className="text-slate-400">—</span> : caps.map((a) => (
                      <div key={a.subject_id}>
                        <span className="font-medium">{subjectName(a.subject_id)}</span>
                        <span className="text-slate-500"> → {a.grades.join(", ") || "—"}</span>
                      </div>
                    ))}
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
                  <td className="px-4 py-2 whitespace-nowrap">
                    <div className="flex gap-2">
                      <button onClick={() => handleEdit(teacher)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded">Edit</button>
                      <button onClick={() => setPrefTeacher(teacher)} className="bg-white hover:bg-purple-50 text-purple-700 border border-purple-300 text-sm font-medium px-3 py-1.5 rounded">Preferences</button>
                      <button onClick={() => handleDelete(teacher.id)} className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-3 py-1.5 rounded">Delete</button>
                    </div>
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
