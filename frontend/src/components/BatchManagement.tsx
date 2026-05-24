import React, { useState, useEffect } from "react";
import { api } from "../api";

interface Batch {
  id: number;
  grade: string;
  section: string;
  student_count: number;
}

export default function BatchManagement() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    grade: "",
    section: "",
    student_count: 30,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.admin.batches.list();
      setBatches(res || []);
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
    });
    setEditingId(batch.id);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      grade: "",
      section: "",
      student_count: 30,
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
          <div className="grid grid-cols-3 gap-4">
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
              <th className="px-4 py-2 text-left">Grade</th>
              <th className="px-4 py-2 text-left">Section</th>
              <th className="px-4 py-2 text-left">Students</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {batches.map((batch) => (
              <tr key={batch.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-2">{batch.grade}</td>
                <td className="px-4 py-2">{batch.section}</td>
                <td className="px-4 py-2">{batch.student_count}</td>
                <td className="px-4 py-2 space-x-2">
                  <button onClick={() => handleEdit(batch)} className="text-blue-600 hover:underline text-sm">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(batch.id)} className="text-red-600 hover:underline text-sm">
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
