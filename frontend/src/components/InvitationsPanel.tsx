import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

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
  { value: "admin", label: "Admin" },
  { value: "principal", label: "Principal" },
  { value: "coordinator", label: "Coordinator" },
  { value: "teacher", label: "Teacher" },
  { value: "student", label: "Student" },
  { value: "parent", label: "Parent" },
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
  // Tokens are stored hashed server-side, so an invite link is only available
  // once — right after it's created/regenerated. Keep it here for copying.
  const [freshLink, setFreshLink] = useState<{ email: string; link: string } | null>(null);

  const currentRole = useAuthStore((s) => s.user?.role);
  // Only an admin/owner may mint another admin (matches the backend guard).
  const availableRoles = ROLES.filter(
    (r) => r.value !== "admin" || currentRole === "admin"
  );

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
      const res = await api.invitations.create({ email: email.trim(), name: name.trim(), role });
      if (res?.invite_link) setFreshLink({ email: res.email, link: fullLink(res.invite_link) });
      setEmail("");
      setName("");
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not create invitation.");
    } finally {
      setBusy(false);
    }
  };

  // Re-issue a pending invite to mint a fresh one-time link.
  const regenerate = async (inv: Invite) => {
    setError("");
    try {
      const res = await api.invitations.create({ email: inv.email, name: inv.name || "", role: inv.role });
      if (res?.invite_link) setFreshLink({ email: res.email, link: fullLink(res.invite_link) });
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not regenerate the link.");
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Invitations</h2>
        <p className="text-sm text-slate-500">
          Invite staff, students and parents with a secure single-use link (valid 7 days).
          Invitees verify with Google Sign-In using the invited email. Links are shown
          once at creation — copy and share them; use “New link” to re-issue.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
      )}

      {freshLink && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 flex flex-wrap items-center gap-2">
          <span>
            Invite link for <strong>{freshLink.email}</strong> (shown once — copy it now):
          </span>
          <code className="px-2 py-0.5 bg-white rounded border border-emerald-200 text-xs break-all">{freshLink.link}</code>
          <button
            onClick={() => { navigator.clipboard.writeText(freshLink.link); }}
            className="px-2.5 py-1 rounded bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-700"
          >
            Copy
          </button>
          <button onClick={() => setFreshLink(null)} className="text-emerald-500 text-xs hover:text-emerald-700">
            Dismiss
          </button>
        </div>
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
            {availableRoles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
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
                    {inv.status === "pending" ? (
                      <button
                        onClick={() => regenerate(inv)}
                        className="text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                        title="Links are stored hashed, so a new one is minted each time"
                      >
                        New link
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
