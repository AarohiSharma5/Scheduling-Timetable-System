import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Invite {
  id: number;
  email: string;
  name?: string | null;
  role: string;
  status: string;
  expires_at?: string | null;
  accepted_at?: string | null;
  created_at?: string | null;
  invite_link?: string | null;
}

const ROLES = [
  { value: "teacher", label: "Teacher" },
  { value: "principal", label: "Principal" },
  { value: "student", label: "Student" },
];

const statusStyle: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  accepted: "bg-emerald-100 text-emerald-700",
  revoked: "bg-slate-200 text-slate-600",
  expired: "bg-red-100 text-red-700",
};

export default function InvitationsPanel() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("teacher");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setInvites(await api.invitations.list());
    } catch (err: any) {
      setError(err?.response?.data?.error || "Failed to load invitations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const fullLink = (link?: string | null) => (link ? `${window.location.origin}${link}` : "");

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    setBusy(true);
    try {
      await api.invitations.create({ email: email.trim(), name: name.trim(), role });
      setEmail("");
      setName("");
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not create invitation.");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (id: number) => {
    try {
      await api.invitations.revoke(id);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not revoke invitation.");
    }
  };

  const copy = (inv: Invite) => {
    const link = fullLink(inv.invite_link);
    if (!link) return;
    navigator.clipboard.writeText(link);
    setCopied(inv.id);
    setTimeout(() => setCopied((c) => (c === inv.id ? null : c)), 1500);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Invitations</h2>
        <p className="text-sm text-slate-500">
          Invite staff and students with an in-app link. They set their own password when accepting.
          (Email delivery is coming soon — for now, copy and share the link.)
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={create} className="bg-white rounded-xl border border-slate-200 p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div className="sm:col-span-1">
          <label className="block text-xs font-medium text-slate-600 mb-1">Email *</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="person@school.edu"
          />
        </div>
        <div className="sm:col-span-1">
          <label className="block text-xs font-medium text-slate-600 mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Optional"
          />
        </div>
        <div className="sm:col-span-1">
          <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <button
          type="submit"
          disabled={busy}
          className={`px-4 py-2 rounded-lg font-semibold text-white ${busy ? "bg-indigo-400" : "bg-indigo-600 hover:bg-indigo-700"}`}
        >
          {busy ? "Creating…" : "Create invite"}
        </button>
      </form>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <p className="p-4 text-sm text-slate-500">Loading…</p>
        ) : invites.length === 0 ? (
          <p className="p-6 text-sm text-slate-500 text-center">No invitations yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Email</th>
                <th className="text-left px-4 py-2.5 font-medium">Role</th>
                <th className="text-left px-4 py-2.5 font-medium">Status</th>
                <th className="text-left px-4 py-2.5 font-medium">Link</th>
                <th className="text-right px-4 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invites.map((inv) => (
                <tr key={inv.id}>
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-slate-800">{inv.email}</div>
                    {inv.name && <div className="text-xs text-slate-400">{inv.name}</div>}
                  </td>
                  <td className="px-4 py-2.5 capitalize text-slate-700">{inv.role}</td>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusStyle[inv.status] || "bg-slate-100 text-slate-600"}`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    {inv.status === "pending" && inv.invite_link ? (
                      <button
                        onClick={() => copy(inv)}
                        className="text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                      >
                        {copied === inv.id ? "Copied!" : "Copy link"}
                      </button>
                    ) : (
                      <span className="text-slate-300 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {inv.status === "pending" ? (
                      <button
                        onClick={() => revoke(inv.id)}
                        className="px-3 py-1 rounded-lg border border-red-200 text-red-600 text-xs hover:bg-red-50"
                      >
                        Revoke
                      </button>
                    ) : (
                      <span className="text-slate-300 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
