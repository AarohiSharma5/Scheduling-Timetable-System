import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { api } from "../api";

const pwOk = (pw: string) => /^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(pw);

export default function ResetPasswordPage() {
  const { token = "" } = useParams();
  const navigate = useNavigate();

  const [checking, setChecking] = useState(true);
  const [valid, setValid] = useState(false);
  const [email, setEmail] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.auth.resetInfo(token);
        setValid(!!res.valid);
        setEmail(res.email || "");
      } catch (err: any) {
        setError(err?.response?.data?.error || "This reset link is invalid or expired.");
      } finally {
        setChecking(false);
      }
    })();
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!pwOk(next)) {
      setError("Password must be at least 8 characters and include a letter and a number.");
      return;
    }
    if (next !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await api.auth.resetPassword(token, next);
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 p-8">
        <h1 className="text-2xl font-bold text-white mb-1">Reset password</h1>

        {checking ? (
          <p className="text-slate-300 text-sm mt-4">Checking link…</p>
        ) : done ? (
          <div className="mt-4 space-y-4">
            <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-100 text-sm">
              Your password has been reset. You can sign in now.
            </div>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="w-full py-2.5 rounded-lg font-semibold text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Go to sign in
            </button>
          </div>
        ) : !valid ? (
          <div className="mt-4 space-y-4">
            <div className="p-3 rounded-lg bg-red-500/20 border border-red-500 text-red-200 text-sm">
              {error || "This reset link is invalid or expired."}
            </div>
            <Link to="/forgot-password" className="text-sm text-indigo-300 hover:text-indigo-200">
              Request a new link →
            </Link>
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-300 mb-6">For {email}</p>
            {error && (
              <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">{error}</div>
            )}
            <form onSubmit={submit} className="space-y-4">
              <Field label="New password" value={next} onChange={setNext} />
              <Field label="Confirm new password" value={confirm} onChange={setConfirm} />
              <button
                type="submit"
                disabled={loading}
                className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
                  loading ? "bg-slate-600 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700"
                }`}
              >
                {loading ? "Saving…" : "Reset password"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-medium text-white mb-1.5">{label}</label>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
      />
    </div>
  );
}
