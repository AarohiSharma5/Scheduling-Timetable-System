import React, { useEffect, useState } from "react";
import { api } from "../api";

interface ChargeType {
  id: number;
  name: string;
  default_hours_per_week: number;
}

export default function ChargeManagement() {
  const [charges, setCharges] = useState<ChargeType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [hours, setHours] = useState(2);

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      setLoading(true);
      const res = await api.admin.charges.list();
      setCharges(Array.isArray(res) ? res : res.data || []);
    } catch (err) {
      setError("Failed to load charges");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      setError("");
      await api.admin.charges.create({ name: name.trim(), default_hours_per_week: hours });
      setName("");
      setHours(2);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to add charge");
      console.error(err);
    }
  };

  const handleUpdateHours = async (id: number, value: number) => {
    try {
      await api.admin.charges.update(id, { default_hours_per_week: value });
      setCharges((cs) => cs.map((c) => (c.id === id ? { ...c, default_hours_per_week: value } : c)));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this charge type?")) return;
    try {
      await api.admin.charges.delete(id);
      await load();
    } catch (err) {
      setError("Failed to delete charge");
      console.error(err);
    }
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Charges &amp; Duties</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define non-teaching duties (class teacher, clubs, houses, exam duty, …). The hours each carries
          reduce a teacher's teaching capacity so everyone's total weekly contact load stays balanced.
        </p>
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      <form onSubmit={handleAdd} className="bg-white p-4 rounded-lg shadow-md flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Charge name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. House Charge" className="border rounded px-3 py-2 w-64" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Default hours / week</label>
          <input type="number" min={0} max={40} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="border rounded px-3 py-2 w-32" />
        </div>
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">+ Add charge</button>
      </form>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Charge</th>
              <th className="px-4 py-2 text-left">Default hours / week</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {charges.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-6 text-center text-slate-400">No charges defined yet.</td></tr>
            )}
            {charges.map((c) => (
              <tr key={c.id} className="border-b hover:bg-slate-50">
                <td className="px-4 py-2">{c.name}</td>
                <td className="px-4 py-2">
                  <input
                    type="number" min={0} max={40}
                    defaultValue={c.default_hours_per_week}
                    onBlur={(e) => handleUpdateHours(c.id, Number(e.target.value))}
                    className="border rounded px-2 py-1 w-24"
                  />
                </td>
                <td className="px-4 py-2">
                  <button onClick={() => handleDelete(c.id)} className="text-red-600 hover:underline text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
