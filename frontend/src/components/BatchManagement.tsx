import React, { useState, useEffect } from "react";
import { api } from "../api";

interface Batch {
  id: number;
  grade: string;
  section: string;
  student_count: number;
  periods_per_day: number | null;
  homeroom_teacher_id: number | null;
  room_id: number | null;
  capacity: number | null;
}

interface TeacherLite {
  id: number;
  name: string;
  teacher_code?: string;
}

interface RoomLite {
  id: number;
  room_id: string;
  room_name: string;
  room_type: string;
  capacity: number;
  floor: number | null;
}

// Mirror of backend period_utils.is_pre_primary so the homeroom selector only
// appears for Nursery / LKG / UKG / Prep style grades.
const PRE_PRIMARY = new Set([
  "nursery", "prenursery", "playgroup", "pg", "lkg", "ukg", "kg", "kg1", "kg2",
  "kindergarten", "prep", "preparatory", "preprimary", "pp", "pp1", "pp2", "preschool",
]);
const isPrePrimary = (grade: string): boolean => {
  const n = String(grade || "").toLowerCase().replace(/[^a-z0-9 ]/g, "").trim();
  return PRE_PRIMARY.has(n) || PRE_PRIMARY.has(n.replace(/ /g, ""));
};

export default function BatchManagement() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [teachers, setTeachers] = useState<TeacherLite[]>([]);
  const [rooms, setRooms] = useState<RoomLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    grade: "",
    section: "",
    student_count: 30,
    periods_per_day: "" as number | "",
    homeroom_teacher_id: "" as number | "",
    room_id: "" as number | "",
    capacity: "" as number | "",
  });

  // "Set day length by grade" controls.
  const [bulkGrade, setBulkGrade] = useState("");
  const [bulkPeriods, setBulkPeriods] = useState<number | "">("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkMsg, setBulkMsg] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  // Distinct grades, in the order they first appear.
  const grades = batches.reduce<string[]>((acc, b) => {
    if (!acc.includes(b.grade)) acc.push(b.grade);
    return acc;
  }, []);

  const applyBulkDayLength = async () => {
    if (!bulkGrade) return;
    setBulkBusy(true);
    setBulkMsg("");
    setError("");
    try {
      const targets = batches.filter((b) => b.grade === bulkGrade);
      const value = bulkPeriods === "" ? null : Number(bulkPeriods);
      await Promise.all(
        targets.map((b) => api.admin.batches.update(b.id, { periods_per_day: value }))
      );
      await loadData();
      setBulkMsg(
        `Updated ${targets.length} section(s) of grade ${bulkGrade} to ${
          value === null ? "full day (school default)" : `${value} periods/day`
        }.`
      );
    } catch (err) {
      setError("Failed to bulk-update day length");
      console.error(err);
    } finally {
      setBulkBusy(false);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [res, teacherRes, roomRes] = await Promise.all([
        api.admin.batches.list(),
        api.admin.teachers.list().catch(() => []),
        api.admin.rooms.list().catch(() => []),
      ]);
      setBatches(res || []);
      setTeachers((teacherRes || []).map((t: any) => ({ id: t.id, name: t.name, teacher_code: t.teacher_code })));
      setRooms(roomRes || []);
    } catch (err) {
      setError("Failed to load batches");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.admin.batches.update(editingId, formData);
      } else {
        await api.admin.batches.create(formData);
      }
      await loadData();
      resetForm();
    } catch (err) {
      setError("Failed to save batch");
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this batch?")) return;
    try {
      await api.admin.batches.delete(id);
      await loadData();
    } catch (err) {
      setError("Failed to delete batch");
      console.error(err);
    }
  };

  const handleEdit = (batch: Batch) => {
    setFormData({
      grade: batch.grade,
      section: batch.section,
      student_count: batch.student_count,
      periods_per_day: batch.periods_per_day ?? "",
      homeroom_teacher_id: batch.homeroom_teacher_id ?? "",
      room_id: batch.room_id ?? "",
      capacity: batch.capacity ?? "",
    });
    setEditingId(batch.id);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      grade: "",
      section: "",
      student_count: 30,
      periods_per_day: "",
      homeroom_teacher_id: "",
      room_id: "",
      capacity: "",
    });
    setEditingId(null);
    setShowForm(false);
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-900">Batches</h2>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            + Add Batch
          </button>
        )}
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <input
              type="text"
              placeholder="Grade (e.g., 9, 10, 11, 12)"
              value={formData.grade}
              onChange={(e) => setFormData({ ...formData, grade: e.target.value })}
              className="border rounded px-3 py-2"
              required
            />
            <input
              type="text"
              placeholder="Section (e.g., A, B, C)"
              value={formData.section}
              onChange={(e) => setFormData({ ...formData, section: e.target.value })}
              className="border rounded px-3 py-2"
              required
            />
            <input
              type="number"
              placeholder="Student Count"
              value={formData.student_count}
              onChange={(e) => setFormData({ ...formData, student_count: Number(e.target.value) })}
              className="border rounded px-3 py-2"
              min="1"
              max="100"
              required
            />
            <div>
              <input
                type="number"
                placeholder="Periods/day (blank = full day)"
                value={formData.periods_per_day}
                onChange={(e) => setFormData({ ...formData, periods_per_day: e.target.value ? Number(e.target.value) : "" })}
                className="border rounded px-3 py-2 w-full"
                min="1"
                max="12"
              />
              <p className="text-xs text-slate-500 mt-1">Shorter day for juniors. Blank = school default.</p>
            </div>
          </div>

          {isPrePrimary(formData.grade) && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Homeroom teacher (pre-primary)
              </label>
              <select
                value={formData.homeroom_teacher_id}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    homeroom_teacher_id: e.target.value ? Number(e.target.value) : "",
                  })
                }
                className="border rounded px-3 py-2 w-full md:w-80"
              >
                <option value="">Use class teacher of this section</option>
                {teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}{t.teacher_code ? ` (${t.teacher_code})` : ""}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                In <strong>Single Teacher Mode</strong> this teacher takes most subjects for the class.
                Leave blank to use the section's class teacher.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Home classroom (fixed)</label>
              <select
                value={formData.room_id}
                onChange={(e) => {
                  const id = e.target.value ? Number(e.target.value) : "";
                  const room = rooms.find((r) => r.id === id);
                  setFormData({
                    ...formData,
                    room_id: id,
                    // Default the section capacity to the chosen room's capacity.
                    capacity: room && formData.capacity === "" ? room.capacity : formData.capacity,
                  });
                }}
                className="border rounded px-3 py-2 w-full"
              >
                <option value="">Not assigned</option>
                {rooms
                  .filter((r) => r.room_type === "regular")
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.room_id} — {r.room_name} (cap {r.capacity})
                    </option>
                  ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">Students stay here for regular subjects; teachers come to them.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Section capacity</label>
              <input
                type="number"
                placeholder="blank = room / school default"
                value={formData.capacity}
                onChange={(e) => setFormData({ ...formData, capacity: e.target.value ? Number(e.target.value) : "" })}
                className="border rounded px-3 py-2 w-full"
                min="1"
                max="200"
              />
              <p className="text-xs text-slate-500 mt-1">Max students in this section. Distribution never exceeds it.</p>
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

      {/* Set day length for a whole grade at once (younger grades end earlier) */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-slate-900 mb-1">Set day length by grade</h3>
        <p className="text-sm text-slate-600 mb-3">
          Choose how many periods a grade runs each day. Leave the number blank to use the
          school-wide day. This is what lets younger grades finish earlier.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Grade</label>
            <select
              value={bulkGrade}
              onChange={(e) => setBulkGrade(e.target.value)}
              className="border rounded px-3 py-2"
            >
              <option value="">Select grade…</option>
              {grades.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Periods/day</label>
            <input
              type="number"
              min="1"
              max="12"
              placeholder="blank = full day"
              value={bulkPeriods}
              onChange={(e) => setBulkPeriods(e.target.value ? Number(e.target.value) : "")}
              className="border rounded px-3 py-2 w-40"
            />
          </div>
          <button
            type="button"
            onClick={applyBulkDayLength}
            disabled={!bulkGrade || bulkBusy}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded"
          >
            {bulkBusy ? "Applying…" : "Apply to grade"}
          </button>
        </div>
        {bulkMsg && <p className="text-sm text-green-700 mt-2">{bulkMsg}</p>}
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Grade</th>
              <th className="px-4 py-2 text-left">Section</th>
              <th className="px-4 py-2 text-left">Students</th>
              <th className="px-4 py-2 text-left">Periods/Day</th>
              <th className="px-4 py-2 text-left">Home room</th>
              <th className="px-4 py-2 text-left">Capacity</th>
              <th className="px-4 py-2 text-left">Homeroom</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {batches.map((batch) => (
              <tr key={batch.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-2">{batch.grade}</td>
                <td className="px-4 py-2">{batch.section}</td>
                <td className="px-4 py-2">{batch.student_count}</td>
                <td className="px-4 py-2">{batch.periods_per_day ?? <span className="text-slate-400">full day</span>}</td>
                <td className="px-4 py-2">
                  {batch.room_id
                    ? (() => {
                        const r = rooms.find((x) => x.id === batch.room_id);
                        return r ? `${r.room_id} — ${r.room_name}` : `#${batch.room_id}`;
                      })()
                    : <span className="text-slate-400">unassigned</span>}
                </td>
                <td className="px-4 py-2">{batch.capacity ?? <span className="text-slate-400">default</span>}</td>
                <td className="px-4 py-2">
                  {isPrePrimary(batch.grade)
                    ? (batch.homeroom_teacher_id
                        ? (teachers.find((t) => t.id === batch.homeroom_teacher_id)?.name ?? `#${batch.homeroom_teacher_id}`)
                        : <span className="text-slate-400">class teacher</span>)
                    : <span className="text-slate-300">—</span>}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  <div className="flex gap-2">
                    <button onClick={() => handleEdit(batch)} className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded">
                      Edit
                    </button>
                    <button onClick={() => handleDelete(batch.id)} className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-3 py-1.5 rounded">
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
