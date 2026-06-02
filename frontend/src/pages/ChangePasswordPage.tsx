import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

const pwOk = (pw: string) => /^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(pw);

export default function ChangePasswordPage() {
  const { user, getCurrentUser } = useAuthStore();
  const navigate = useNavigate();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const firstLogin = !!user?.must_change_password;
  const needsProfile = firstLogin && !user?.profile_completed;

  const dashboardFor = (role?: string) => `/${role || "teacher"}`;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!pwOk(next)) {
      setError("New password must be at least 8 characters and include a letter and a number.");
      return;
    }
    if (next !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await api.auth.changePassword({
        current_password: current,
        new_password: next,
        complete_profile: needsProfile ? { name: name.trim(), phone: phone.trim() } : undefined,
      });
      await getCurrentUser();
      navigate(dashboardFor(user?.role), { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not update password.");
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    navigate("/login", { replace: true });
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 p-8">
        <h1 className="text-2xl font-bold text-white mb-1">
          {firstLogin ? "Set your password" : "Change password"}
        </h1>
        <p className="text-sm text-slate-300 mb-6">
          {firstLogin
            ? "You're signing in with a temporary password. Choose a new one to continue."
            : "Update the password for your account."}
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <Field label={firstLogin ? "Temporary password" : "Current password"} type="password" value={current} onChange={setCurrent} required />
          <Field label="New password" type="password" value={next} onChange={setNext} required />
          <Field label="Confirm new password" type="password" value={confirm} onChange={setConfirm} required />

          {needsProfile && (
            <>
              <div className="pt-2 border-t border-white/10" />
              <p className="text-xs uppercase tracking-wide text-indigo-300">Complete your profile</p>
              <Field label="Full name" type="text" value={name} onChange={setName} required />
              <Field label="Phone (optional)" type="text" value={phone} onChange={setPhone} />
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
              loading ? "bg-slate-600 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700"
            }`}
          >
            {loading ? "Saving…" : firstLogin ? "Set password & continue" : "Update password"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Field({
  label, type, value, onChange, required,
}: { label: string; type: string; value: string; onChange: (v: string) => void; required?: boolean }) {
  return (
    <div>
      <label className="block text-sm font-medium text-white mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
      />
    </div>
  );
}
