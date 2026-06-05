import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useOrgStore } from "../stores/orgStore";

// Map an authenticated user's real role to its dashboard route. Owner is
// treated as admin (matches the backend role assignment at signup).
const ROLE_ROUTES: Record<string, string> = {
  admin: "/admin",
  owner: "/admin",
  principal: "/principal",
  teacher: "/teacher",
  student: "/student",
  parent: "/parent",
};

// Demo credentials are only useful against a seeded dev database and must never
// be advertised on a real deployment.
const SHOW_DEMO = process.env.NODE_ENV !== "production";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { login } = useAuthStore();
  const { organization, logoutOrg } = useOrgStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
      // Force temporary-password holders through the first-login flow before
      // they can reach their dashboard.
      if (user?.must_change_password) {
        navigate("/change-password", { replace: true });
        return;
      }
      // Route by the account's actual role from the server — no role selection,
      // so there's no mismatch to reconcile.
      const target = ROLE_ROUTES[user?.role || ""];
      if (!target) {
        setError(
          "Your account doesn't have a dashboard configured yet. Please contact your administrator."
        );
        return;
      }
      navigate(target);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchOrg = () => {
    logoutOrg();
    navigate("/org-login", { replace: true });
  };

  if (!organization) return null;

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex flex-col">
      {/* Decorative background blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -left-24 h-96 w-96 rounded-full bg-indigo-600/30 blur-3xl animate-pulse" />
        <div className="absolute top-1/3 -right-24 h-96 w-96 rounded-full bg-purple-600/20 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-blue-600/20 blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "44px 44px",
          }}
        />
      </div>

      {/* Org banner */}
      <div className="relative z-10 bg-slate-950/50 backdrop-blur-md border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3 group">
            <img
              src={organization.logo_url || "/scheduler-logo.png"}
              alt="logo"
              className="h-9 w-9 object-contain rounded-lg ring-1 ring-white/10"
            />
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-300/80">
                Organisation
              </p>
              <p className="text-sm font-semibold text-white group-hover:text-indigo-300 transition">
                {organization.name}
              </p>
            </div>
          </Link>
          <button
            onClick={handleSwitchOrg}
            className="text-xs sm:text-sm text-slate-200 hover:text-white px-3.5 py-1.5 rounded-full border border-white/15 hover:border-white/40 bg-white/5 hover:bg-white/10 transition"
          >
            Switch organisation
          </button>
        </div>
      </div>

      <div className="relative z-10 flex-1 flex items-center justify-center p-4 py-10">
        <div className="max-w-md w-full">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center h-16 w-16 mb-5 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-900/50 text-3xl ring-1 ring-white/20">
              📅
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3 bg-gradient-to-r from-white via-indigo-100 to-indigo-300 bg-clip-text text-transparent">
              School Timetable Scheduler
            </h1>
            <p className="text-slate-300/90 text-base">
              Sign in to {organization.name}
            </p>
          </div>

          <div className="bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl shadow-indigo-950/40 border border-white/10 p-8">
            {error && (
              <div className="mb-4 p-4 bg-red-500/20 border border-red-500 rounded text-red-200">
                {error}
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  autoFocus
                  className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full py-2.5 rounded-lg font-semibold text-white transition shadow-lg ${
                  loading
                    ? "bg-slate-600 cursor-not-allowed"
                    : "bg-gradient-to-r from-indigo-500 to-purple-600 hover:shadow-xl hover:brightness-110"
                }`}
              >
                {loading ? "Signing in…" : "Sign In"}
              </button>
            </form>

            <div className="mt-4 text-center">
              <Link
                to="/forgot-password"
                className="text-sm text-indigo-300 hover:text-indigo-200 transition"
              >
                Forgot password?
              </Link>
            </div>

            {SHOW_DEMO && (
              <div className="mt-6 p-4 bg-slate-900/50 border border-white/10 rounded-lg text-sm text-slate-300">
                <p className="font-semibold mb-2">Demo credentials (dev only):</p>
                <div className="space-y-1 font-mono text-xs">
                  <p>
                    <strong>Admin:</strong> admin@school.edu / admin123
                  </p>
                  <p>
                    <strong>Principal:</strong> principal@school.edu / principal123
                  </p>
                  <p>
                    <strong>Teacher:</strong> priya.sharma@school.edu / teacher123
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
