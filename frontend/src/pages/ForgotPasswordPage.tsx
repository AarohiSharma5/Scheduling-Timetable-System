import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useOrgStore } from "../stores/orgStore";

export default function ForgotPasswordPage() {
  const { organization } = useOrgStore();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [resetLink, setResetLink] = useState<string | null>(null);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.auth.forgotPassword(email.trim());
      setResetLink(res.reset_link || null);
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not process the request.");
    } finally {
      setLoading(false);
    }
  };

  const fullLink = resetLink ? `${window.location.origin}${resetLink}` : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 p-8">
        <h1 className="text-2xl font-bold text-white mb-1">Reset your password</h1>
        <p className="text-sm text-slate-300 mb-6">
          {organization ? `For ${organization.name}. ` : ""}Enter your account email to get a reset link.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">{error}</div>
        )}

        {!done ? (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-white mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
                loading ? "bg-slate-600 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700"
              }`}
            >
              {loading ? "Generating…" : "Generate reset link"}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-100 text-sm">
              If an account exists for that email, a reset link has been generated.
            </div>
            {fullLink && (
              <div>
                <p className="text-xs text-slate-300 mb-1">In-app reset link (email delivery coming soon):</p>
                <div className="flex gap-2">
                  <input
                    readOnly
                    value={fullLink}
                    className="flex-1 px-3 py-2 rounded-lg bg-slate-900/60 border border-white/10 text-indigo-200 font-mono text-xs"
                  />
                  <button
                    onClick={() => navigator.clipboard.writeText(fullLink)}
                    className="px-3 rounded-lg border border-indigo-300 text-indigo-200 text-sm hover:bg-indigo-500/20"
                  >
                    Copy
                  </button>
                </div>
                <Link to={resetLink!} className="inline-block mt-3 text-sm text-indigo-300 hover:text-indigo-200">
                  Open reset page →
                </Link>
              </div>
            )}
          </div>
        )}

        <div className="mt-6 text-center">
          <Link to="/login" className="text-sm text-slate-300 hover:text-white">← Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
