import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useOrgStore } from "../stores/orgStore";

type Role = "admin" | "principal" | "teacher" | "student";

const loginOptions: Record<
  Role,
  { label: string; icon: string; color: string; description: string }
> = {
  admin: {
    label: "Admin",
    icon: "⚙️",
    color: "from-red-500 to-red-600",
    description: "Manage school, teachers, and schedules",
  },
  principal: {
    label: "Principal",
    icon: "👨‍💼",
    color: "from-blue-500 to-blue-600",
    description: "View all timetables and reports",
  },
  teacher: {
    label: "Teacher",
    icon: "👨‍🏫",
    color: "from-green-500 to-green-600",
    description: "View your classes and schedule",
  },
  student: {
    label: "Student",
    icon: "👨‍🎓",
    color: "from-purple-500 to-purple-600",
    description: "View your class schedule",
  },
};

export default function LoginPage() {
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
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
      } else {
        navigate(`/${selectedRole}`);
      }
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
        <div className="max-w-6xl w-full">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center h-16 w-16 mb-5 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-900/50 text-3xl ring-1 ring-white/20">
              📅
            </div>
            <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-3 bg-gradient-to-r from-white via-indigo-100 to-indigo-300 bg-clip-text text-transparent">
              School Timetable Scheduler
            </h1>
            <p className="text-slate-300/90 text-base sm:text-lg">
              {selectedRole
                ? `Sign in as ${loginOptions[selectedRole].label}`
                : "Choose how you'd like to sign in"}
            </p>
          </div>

          {!selectedRole ? (
            // Role Selector
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {(
                Object.entries(loginOptions) as [
                  Role,
                  typeof loginOptions[Role]
                ][]
              ).map(([role, option]) => (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  className="group relative overflow-hidden p-6 rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl text-left transition-all duration-300 hover:-translate-y-1.5 hover:border-white/25 hover:bg-white/[0.07] hover:shadow-2xl hover:shadow-indigo-900/40"
                >
                  {/* hover gradient sheen */}
                  <div className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 bg-gradient-to-br ${option.color}`} />
                  <div className={`relative mb-4 inline-flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${option.color} text-3xl shadow-lg ring-1 ring-white/20`}>
                    {option.icon}
                  </div>
                  <h3 className="relative text-xl font-bold text-white mb-1">
                    {option.label}
                  </h3>
                  <p className="relative text-sm text-slate-400 leading-snug">{option.description}</p>
                  <span className="relative mt-4 inline-flex items-center gap-1 text-sm font-medium text-indigo-300 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all">
                    Continue
                    <span aria-hidden>→</span>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            // Login Form
            <div className="max-w-md mx-auto">
              <div className="bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl shadow-indigo-950/40 border border-white/10 p-8">
                <button
                  onClick={() => {
                    setSelectedRole(null);
                    setEmail("");
                    setPassword("");
                    setError("");
                  }}
                  className="text-slate-300 hover:text-white mb-5 inline-flex items-center gap-2 bg-transparent border-0 p-0 transition"
                >
                  <span aria-hidden>←</span> Back to roles
                </button>

                <div className="mb-6">
                  <div
                    className={`inline-block px-4 py-2 rounded-full bg-gradient-to-r ${loginOptions[selectedRole].color} text-white font-semibold`}
                  >
                    {loginOptions[selectedRole].icon}{" "}
                    {loginOptions[selectedRole].label}
                  </div>
                </div>

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
                        : `bg-gradient-to-r ${loginOptions[selectedRole].color} hover:shadow-xl hover:brightness-110`
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

                <div className="mt-6 p-4 bg-slate-900/50 border border-white/10 rounded-lg text-sm text-slate-300">
                  <p className="font-semibold mb-2">Demo credentials:</p>
                  <div className="space-y-1 font-mono text-xs">
                    <p>
                      <strong>Admin:</strong> admin@school.edu / admin123
                    </p>
                    <p>
                      <strong>Principal:</strong> principal@school.edu /
                      principal123
                    </p>
                    <p>
                      <strong>Teacher:</strong> priya.sharma@school.edu /
                      teacher123
                    </p>
                    <p>
                      <strong>Student:</strong> student9A1@school.edu /
                      student123
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
