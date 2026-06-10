import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

const ROLE_ROUTES: Record<string, string> = {
  admin: "/admin",
  owner: "/admin",
  principal: "/principal",
  coordinator: "/coordinator",
  teacher: "/teacher",
  student: "/student",
  parent: "/parent",
};

/** First-time profile setup shown right after an invitation is accepted. */
export default function FirstTimeSetupPage() {
  const { user, getCurrentUser } = useAuthStore();
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [photo, setPhoto] = useState(user?.profile_photo || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const dashboard = ROLE_ROUTES[user?.role || ""] || "/login";

  const finish = async (skip: boolean) => {
    setError("");
    setSaving(true);
    try {
      await api.auth.completeProfile(
        skip ? {} : { name: name.trim(), phone: phone.trim(), profile_photo: photo.trim() }
      );
      await getCurrentUser();
      navigate(dashboard, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not save your profile.");
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    navigate("/login", { replace: true });
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 p-8">
        <h1 className="text-2xl font-bold text-white mb-1">Welcome, {user.name?.split(" ")[0]} 👋</h1>
        <p className="text-sm text-slate-300 mb-6">
          You've joined as <span className="capitalize font-semibold text-indigo-300">{user.role}</span>.
          Finish setting up your profile — you can change this later.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">{error}</div>
        )}

        <div className="flex justify-center mb-5">
          {photo ? (
            <img
              src={photo}
              alt="profile preview"
              className="h-20 w-20 rounded-full object-cover ring-2 ring-indigo-400/50"
              onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
            />
          ) : (
            <div className="h-20 w-20 rounded-full bg-indigo-500/30 ring-2 ring-indigo-400/40 flex items-center justify-center text-3xl text-indigo-100">
              {(user.name || "?").charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            finish(false);
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-white mb-1.5">Full name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-white mb-1.5">Contact number</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Optional"
              className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-white mb-1.5">Profile photo URL</label>
            <input
              type="url"
              value={photo}
              onChange={(e) => setPhoto(e.target.value)}
              placeholder="https://… (optional)"
              className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
              saving ? "bg-slate-600 cursor-not-allowed" : "bg-gradient-to-r from-indigo-500 to-purple-600 hover:brightness-110"
            }`}
          >
            {saving ? "Saving…" : "Save & continue"}
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => finish(true)}
            className="w-full py-2 rounded-lg text-sm text-slate-300 hover:text-white transition"
          >
            Skip for now
          </button>
        </form>
      </div>
    </div>
  );
}
