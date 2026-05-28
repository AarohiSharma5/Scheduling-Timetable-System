import React, { useEffect, useState } from "react";
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

  // Require an organization session before user login.
  useEffect(() => {
    if (!organization) {
      navigate("/org-login", { replace: true });
    }
  }, [organization, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate(`/${selectedRole}`);
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex flex-col">
      {/* Org banner */}
      <div className="bg-slate-950/60 border-b border-slate-700">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3 group">
            <img
              src={organization.logo_url || "/scheduler-logo.png"}
              alt="logo"
              className="h-8 w-8 object-contain rounded"
            />
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-400">
                Organisation
              </p>
              <p className="text-sm font-semibold text-white group-hover:text-indigo-300 transition">
                {organization.name}
              </p>
            </div>
          </Link>
          <button
            onClick={handleSwitchOrg}
            className="text-xs sm:text-sm text-slate-300 hover:text-white px-3 py-1.5 rounded border border-slate-600 hover:border-slate-400 bg-transparent"
          >
            Switch organisation
          </button>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-6xl w-full">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-white mb-2">
              📅 School Timetable Scheduler
            </h1>
            <p className="text-slate-300">
              {selectedRole
                ? `Sign in as ${loginOptions[selectedRole].label}`
                : "Select your role to log in"}
            </p>
          </div>

          {!selectedRole ? (
            // Role Selector
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {(
                Object.entries(loginOptions) as [
                  Role,
                  typeof loginOptions[Role]
                ][]
              ).map(([role, option]) => (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  className="p-6 rounded-lg border-2 border-slate-700 hover:border-slate-500 transition transform hover:scale-105 bg-slate-800 text-left"
                >
                  <div className="text-4xl mb-3">{option.icon}</div>
                  <h3 className="text-xl font-bold text-white mb-1">
                    {option.label}
                  </h3>
                  <p className="text-sm text-slate-400">{option.description}</p>
                </button>
              ))}
            </div>
          ) : (
            // Login Form
            <div className="max-w-md mx-auto">
              <div className="bg-slate-800 rounded-lg shadow-xl p-8">
                <button
                  onClick={() => {
                    setSelectedRole(null);
                    setEmail("");
                    setPassword("");
                    setError("");
                  }}
                  className="text-slate-400 hover:text-slate-200 mb-4 flex items-center gap-2 bg-transparent border-0 p-0"
                >
                  ← Back to roles
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
                      className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white placeholder-slate-400 focus:border-blue-500 focus:outline-none"
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
                      className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white placeholder-slate-400 focus:border-blue-500 focus:outline-none"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className={`w-full py-2 rounded-lg font-semibold text-white transition ${
                      loading
                        ? "bg-slate-600 cursor-not-allowed"
                        : `bg-gradient-to-r ${loginOptions[selectedRole].color} hover:shadow-lg`
                    }`}
                  >
                    {loading ? "Signing in…" : "Sign In"}
                  </button>
                </form>

                <div className="mt-6 p-4 bg-slate-700 rounded text-sm text-slate-300">
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
