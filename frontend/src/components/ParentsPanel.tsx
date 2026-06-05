import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Child {
  student_id: number;
  name: string;
  class: string;
  roll_no: number | null;
}

interface ParentRow {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  status: string;
  children: Child[];
}

interface StudentResult {
  id: number;
  full_name: string;
  class_grade: string;
  section: string;
  admission_no: string;
}

export default function ParentsPanel() {
  const [parents, setParents] = useState<ParentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [relation, setRelation] = useState("guardian");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StudentResult[]>([]);
  const [selected, setSelected] = useState<StudentResult[]>([]);
  const [saving, setSaving] = useState(false);
  const [credentials, setCredentials] = useState<{ email: string; temporary_password: string | null } | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setParents(await api.parents.list());
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't load parents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const search = async () => {
    if (!query.trim()) return;
    try {
      const res = await api.admin.students.list({ q: query.trim() });
      setSearchResults(res);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Search failed.");
    }
  };

  const addChild = (s: StudentResult) => {
    if (!selected.some((x) => x.id === s.id)) setSelected((xs) => [...xs, s]);
  };
  const removeChild = (id: number) => setSelected((xs) => xs.filter((x) => x.id !== id));

  const resetForm = () => {
    setName(""); setEmail(""); setPhone(""); setRelation("guardian");
    setQuery(""); setSearchResults([]); setSelected([]);
  };

  const submit = async () => {
    if (!name.trim() || !email.trim()) {
      setErr("Parent name and email are required.");
      return;
    }
    if (selected.length === 0) {
      setErr("Link at least one child.");
      return;
    }
    try {
      setSaving(true);
      setErr("");
      const res = await api.parents.create({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        relation,
        student_ids: selected.map((s) => s.id),
      });
      setCredentials(res.credentials);
      resetForm();
      setShowForm(false);
      await load();
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't create the parent account.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Remove this parent account?")) return;
    try {
      await api.parents.remove(id);
      setParents((xs) => xs.filter((x) => x.id !== id));
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't remove the parent.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center">
        <h3 className="text-lg font-bold text-slate-800">👪 Parents</h3>
        <button
          onClick={() => { setShowForm((v) => !v); setErr(""); setCredentials(null); }}
          className="ml-auto px-4 py-2 rounded-lg font-medium bg-green-600 text-white hover:bg-green-700"
        >
          {showForm ? "Close" : "+ Add Parent"}
        </button>
      </div>

      {err && <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm">{err}</div>}

      {credentials && (
        <div className="bg-green-50 border border-green-300 text-green-900 px-4 py-3 rounded-lg text-sm">
          <p className="font-semibold">Parent account created.</p>
          <p>Login email: <span className="font-mono">{credentials.email}</span></p>
          {credentials.temporary_password && (
            <p>Temporary password: <span className="font-mono">{credentials.temporary_password}</span> — share it securely; they'll be asked to change it on first login.</p>
          )}
        </div>
      )}

      {showForm && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Parent name"
                   className="border rounded px-3 py-2 bg-white" />
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
                   className="border rounded px-3 py-2 bg-white" />
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone (optional)"
                   className="border rounded px-3 py-2 bg-white" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Relation</label>
            <select value={relation} onChange={(e) => setRelation(e.target.value)}
                    className="border rounded px-3 py-2 bg-white">
              <option value="father">Father</option>
              <option value="mother">Mother</option>
              <option value="guardian">Guardian</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Link children</label>
            <div className="flex gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                placeholder="Search students by name or admission no…"
                className="border rounded px-3 py-2 bg-white flex-1"
              />
              <button onClick={search} className="bg-slate-700 text-white px-4 rounded-lg">Search</button>
            </div>

            {searchResults.length > 0 && (
              <div className="mt-2 border border-slate-200 rounded-lg divide-y max-h-48 overflow-y-auto bg-white">
                {searchResults.map((s) => (
                  <button key={s.id} onClick={() => addChild(s)}
                          className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm">
                    {s.full_name} <span className="text-slate-400">· {s.class_grade}-{s.section} · {s.admission_no}</span>
                  </button>
                ))}
              </div>
            )}

            {selected.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {selected.map((s) => (
                  <span key={s.id} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                    {s.full_name}
                    <button onClick={() => removeChild(s.id)} className="ml-1 text-blue-600 hover:text-blue-900">×</button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <button onClick={submit} disabled={saving}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold py-2 px-5 rounded-lg">
            {saving ? "Creating…" : "Create Parent Account"}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500 text-sm">⏳ Loading…</p>
      ) : parents.length === 0 ? (
        <p className="text-slate-500 text-sm">No parent accounts yet.</p>
      ) : (
        <div className="border border-slate-200 rounded-lg divide-y">
          {parents.map((p) => (
            <div key={p.id} className="flex items-center gap-3 px-3 py-2">
              <div className="flex-1">
                <p className="font-medium text-slate-800">{p.name}</p>
                <p className="text-xs text-slate-500">{p.email}{p.phone ? ` · ${p.phone}` : ""}</p>
              </div>
              <div className="flex flex-wrap gap-1 justify-end max-w-[50%]">
                {p.children.map((c) => (
                  <span key={c.student_id} className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full text-xs">
                    {c.name} ({c.class})
                  </span>
                ))}
              </div>
              <button onClick={() => remove(p.id)} className="text-xs text-red-600 hover:text-red-800 ml-2">Remove</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
