import React, { useState, useEffect } from "react";
import { api } from "../api";

interface Subject {
  id: number;
  name: string;
  periods_per_week: number;
  max_periods_per_day: number;
  requires_double: boolean;
}

export default function SubjectManagement() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    periods_per_week: 3,
    max_periods_per_day: 1,
    requires_double: false,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.admin.subjects.list();
      setSubjects(res || []);
    } catch (err) {
      setError("Failed to load subjects");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.admin.subjects.update(editingId, formData);
      } else {
        await api.admin.subjects.create(formData);
      }
      await loadData();
      resetForm();
    } catch (err) {
      setError("Failed to save subject");
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this subject?")) return;
    try {
      await api.admin.subjects.delete(id);
      await loadData();
    } catch (err) {
      setError("Failed to delete subject");
      console.error(err);
    }
  };

  const handleEdit = (subject: Subject) => {
    setFormData({
      name: subject.name,
      periods_per_week: subject.periods_per_week,
      max_periods_per_day: subject.max_periods_per_day ?? 1,
      requires_double: subject.requires_double ?? false,
    });
    setEditingId(subject.id);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      periods_per_week: 3,
      max_periods_per_day: 1,
      requires_double: false,
    });
    setEditingId(null);
    setShowForm(false);
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-900">Subjects</h2>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
            + Add Subject
          </button>
        )}
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Subject Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="border rounded px-3 py-2"
              required
            />
            <input
              type="number"
              placeholder="Periods Per Week"
              value={formData.periods_per_week}
              onChange={(e) => setFormData({ ...formData, periods_per_week: Number(e.target.value) })}
              className="border rounded px-3 py-2"
              min="1"
              max="10"
              required
            />
            <div>
              <label className="block text-sm font-medium mb-1">Max periods per day (spacing)</label>
              <input
                type="number"
                value={formData.max_periods_per_day}
                onChange={(e) => setFormData({ ...formData, max_periods_per_day: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                min="1"
                max="4"
              />
              <p className="text-xs text-slate-500 mt-1">1 = never twice in a day / no back-to-back.</p>
            </div>
            <label className="flex items-center mt-6">
              <input
                type="checkbox"
                checked={formData.requires_double}
                onChange={(e) => setFormData({ ...formData, requires_double: e.target.checked, max_periods_per_day: e.target.checked ? Math.max(2, formData.max_periods_per_day) : formData.max_periods_per_day })}
                className="mr-2"
              />
              Lab / double period (schedule as consecutive pairs)
            </label>
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
              <th className="px-4 py-2 text-left">Subject</th>
              <th className="px-4 py-2 text-left">Periods/Week</th>
              <th className="px-4 py-2 text-left">Max/Day</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {subjects.map((subject) => (
              <tr key={subject.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-2">{subject.name}</td>
                <td className="px-4 py-2">{subject.periods_per_week}</td>
                <td className="px-4 py-2">{subject.max_periods_per_day ?? 1}</td>
                <td className="px-4 py-2">
                  {subject.requires_double ? (
                    <span className="inline-block bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded">Lab / double</span>
                  ) : (
                    <span className="text-slate-400 text-xs">Regular</span>
                  )}
                </td>
                <td className="px-4 py-2 space-x-2">
                  <button onClick={() => handleEdit(subject)} className="text-blue-600 hover:underline text-sm">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(subject.id)} className="text-red-600 hover:underline text-sm">
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
