import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useOrgStore } from "../stores/orgStore";

// Demo credentials only make sense against a seeded dev database.
const SHOW_DEMO = process.env.NODE_ENV !== "production";

export default function OrgLoginPage() {
  const navigate = useNavigate();
  const { loginOrg, loading, organization } = useOrgStore();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (organization) {
      navigate("/login", { replace: true });
    }
  }, [organization, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await loginOrg(identifier.trim(), password);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Organization login failed");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 flex flex-col">
      {/* Top bar */}
      <header className="px-6 lg:px-12 py-5 flex items-center justify-between max-w-7xl mx-auto w-full">
        <Link to="/" className="flex items-center gap-3">
          <img
            src="/scheduler-logo.png"
            alt="Scheduler logo"
            className="h-9 w-9 object-contain"
          />
          <span className="text-lg font-bold text-slate-900">
            ClassSync<span className="text-indigo-600">.</span>
          </span>
        </Link>
        <Link
          to="/"
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          ← Back to home
        </Link>
      </header>

      {/* Card */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
          <div className="flex flex-col items-center text-center">
            <img
              src="/scheduler-logo.png"
              alt="Logo"
              className="h-14 w-14 object-contain"
            />
            <h1 className="mt-4 text-2xl font-bold text-slate-900">
              Login as Organisation
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Step 1 of 2 — authenticate your institute
            </p>
          </div>

          {error && (
            <div className="mt-6 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Organisation
              </label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="Organisation name or slug"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                required
                autoFocus
              />
              <p className="mt-1 text-xs text-slate-500">
                e.g. <span className="font-mono">Test Sample Institute</span> or{" "}
                <span className="font-mono">test-sample-institute</span>
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Organisation password"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
                loading
                  ? "bg-indigo-400 cursor-not-allowed"
                  : "bg-indigo-600 hover:bg-indigo-700"
              }`}
            >
              {loading ? "Signing in…" : "Continue →"}
            </button>
          </form>

          {SHOW_DEMO && (
            <div className="mt-6 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
              <p className="font-semibold text-slate-700 mb-1">Demo credentials (dev only)</p>
              <p>
                Organisation:{" "}
                <span className="font-mono">Test Sample Institute</span>
              </p>
              <p>
                Password: <span className="font-mono">institute123</span>
              </p>
            </div>
          )}

          <p className="mt-6 text-xs text-slate-500 text-center">
            Once you sign in to an organisation, you'll stay signed in to it.
            You can then log in as Admin, Principal, Teacher or Student.
          </p>

          <div className="mt-4 pt-4 border-t border-slate-200 text-center text-sm text-slate-600">
            New school?{" "}
            <Link to="/org-signup" className="font-semibold text-indigo-600 hover:text-indigo-700">
              Register your organisation →
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
