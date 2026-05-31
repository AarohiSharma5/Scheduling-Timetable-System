import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Department {
  id: number;
  name: string;
  default_hours_per_week: number;
  members_required: number;
  takes_classes: boolean;
  assigned_members: number;
}

const emptyForm = { name: "", default_hours_per_week: 2, members_required: 1, takes_classes: true };

export default function ChargeManagement() {
  const [depts, setDepts] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ ...emptyForm });

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      setLoading(true);
      const res = await api.admin.charges.list();
      setDepts(Array.isArray(res) ? res : res.data || []);
    } catch (err) {
      setError("Failed to load departments");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    try {
      setError("");
      await api.admin.charges.create({ ...form, name: form.name.trim() });
      setForm({ ...emptyForm });
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to add department");
      console.error(err);
    }
  };

  const patch = async (id: number, updates: Partial<Department>) => {
    try {
      await api.admin.charges.update(id, updates);
      await load();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this department?")) return;
    try {
      await api.admin.charges.delete(id);
      await load();
    } catch (err) {
      setError("Failed to delete department");
      console.error(err);
    }
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Departments &amp; Charges</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define each department/duty, how many teachers it needs, its weekly contact hours, and whether
          its members also teach classes. Members of non-teaching departments (Library, Fees…) are held back
          as the <strong>substitute pool</strong>. Hours reduce a teacher's teaching capacity so total load stays balanced.
        </p>
      </div>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      <form onSubmit={handleAdd} className="bg-white p-4 rounded-lg shadow-md flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Department / task</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Science Club" className="border rounded px-3 py-2 w-56" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Members required</label>
          <input type="number" min={0} value={form.members_required} onChange={(e) => setForm({ ...form, members_required: Number(e.target.value) })} className="border rounded px-3 py-2 w-32" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Hours / week</label>
          <input type="number" min={0} max={40} value={form.default_hours_per_week} onChange={(e) => setForm({ ...form, default_hours_per_week: Number(e.target.value) })} className="border rounded px-3 py-2 w-28" />
        </div>
        <label className="flex items-center gap-2 mb-2 text-sm">
          <input type="checkbox" checked={form.takes_classes} onChange={(e) => setForm({ ...form, takes_classes: e.target.checked })} />
          Members take classes
        </label>
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">+ Add department</button>
      </form>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left">Department</th>
              <th className="px-4 py-2 text-left">Coverage</th>
              <th className="px-4 py-2 text-left">Hours / week</th>
              <th className="px-4 py-2 text-left">Takes classes</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {depts.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-400">No departments defined yet.</td></tr>
            )}
            {depts.map((d) => {
              const short = d.assigned_members < d.members_required;
              return (
                <tr key={d.id} className="border-b hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">
                    {d.name}
                    {!d.takes_classes && <span className="ml-2 text-xs bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded">substitute pool</span>}
                  </td>
                  <td className="px-4 py-2">
                    <span className={short ? "text-amber-700 font-medium" : "text-green-700"}>
                      {d.assigned_members} / {d.members_required}
                    </span>
                    {short && <span className="text-xs text-amber-600 ml-2">needs {d.members_required - d.assigned_members} more</span>}
                    <div className="mt-1">
                      <input
                        type="number" min={0} defaultValue={d.members_required}
                        onBlur={(e) => patch(d.id, { members_required: Number(e.target.value) })}
                        className="border rounded px-2 py-0.5 w-20 text-sm"
                        title="Members required"
                      />
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number" min={0} max={40} defaultValue={d.default_hours_per_week}
                      onBlur={(e) => patch(d.id, { default_hours_per_week: Number(e.target.value) })}
                      className="border rounded px-2 py-1 w-24"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked={d.takes_classes} onChange={(e) => patch(d.id, { takes_classes: e.target.checked })} />
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleDelete(d.id)} className="text-red-600 hover:underline text-sm">Delete</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
