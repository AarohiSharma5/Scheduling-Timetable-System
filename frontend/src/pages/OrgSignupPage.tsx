import React, { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useOrgStore } from "../stores/orgStore";

const API_BASE = process.env.REACT_APP_API_URL || "/api";

const BOARDS = ["CBSE", "ICSE", "State Board", "IB", "IGCSE", "Other"];
const DESIGNATIONS = [
  { value: "owner", label: "School Owner" },
  { value: "admin", label: "Admin" },
  { value: "principal", label: "Principal" },
];

type Fields = Record<string, string>;

export default function OrgSignupPage() {
  const navigate = useNavigate();
  const { registerOrg, loading } = useOrgStore();
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Fields>({});
  const [done, setDone] = useState<{ email: string; role: string } | null>(null);

  // Organization info
  const [org, setOrg] = useState({
    name: "", school_code: "", board: "CBSE", address: "", city: "", state: "",
    country: "India", postal_code: "", contact_number: "", official_email: "",
    website: "", password: "",
  });
  // Primary account info
  const [admin, setAdmin] = useState({
    full_name: "", designation: "owner", email: "", phone: "", password: "",
  });

  const setO = (k: keyof typeof org) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setOrg((s) => ({ ...s, [k]: e.target.value }));

  // Auto-generate a unique school code from the school name.
  const regenerateCode = useCallback(async (name: string) => {
    try {
      const r = await fetch(`${API_BASE}/organizations/suggest-school-code?name=${encodeURIComponent(name)}`);
      const d = await r.json();
      if (d.school_code) setOrg((s) => ({ ...s, school_code: d.school_code }));
    } catch {
      /* non-fatal; backend will auto-generate on submit anyway */
    }
  }, []);

  useEffect(() => {
    regenerateCode("");
  }, [regenerateCode]);
  const setA = (k: keyof typeof admin) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setAdmin((s) => ({ ...s, [k]: e.target.value }));

  const pwOk = (p: string) => /^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(p);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    const local: Fields = {};
    if (!org.name.trim()) local.name = "Required";
    if (!org.official_email.trim()) local.official_email = "Required";
    if (!pwOk(org.password)) local.org_password = "8+ chars, a letter & a number";
    if (!admin.full_name.trim()) local.full_name = "Required";
    if (!admin.email.trim()) local.admin_email = "Required";
    if (!pwOk(admin.password)) local.admin_password = "8+ chars, a letter & a number";
    if (Object.keys(local).length) {
      setFieldErrors(local);
      setError("Please fix the highlighted fields.");
      return;
    }

    try {
      const res = await registerOrg({ organization: org, admin });
      setDone({ email: res.admin.email, role: res.admin.role });
    } catch (err: any) {
      if (err.fields) setFieldErrors(err.fields);
      setError(err.message || "Signup failed");
    }
  };

  const input = (val: string, onChange: any, placeholder: string, errKey?: string, type = "text", required = false) => (
    <div>
      <input
        type={type}
        value={val}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className={`w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
          errKey && fieldErrors[errKey] ? "border-red-400 bg-red-50" : "border-slate-300"
        }`}
      />
      {errKey && fieldErrors[errKey] && (
        <p className="mt-1 text-xs text-red-600">{fieldErrors[errKey]}</p>
      )}
    </div>
  );

  if (done) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 flex items-center justify-center px-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 p-8 text-center">
          <div className="text-5xl mb-3">🎉</div>
          <h1 className="text-2xl font-bold text-slate-900">Organisation created!</h1>
          <p className="mt-2 text-sm text-slate-600">
            Your school <span className="font-semibold">{org.name}</span> is ready. Sign in with your{" "}
            {done.role} account:
          </p>
          <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200 text-sm">
            <p><span className="text-slate-500">Email:</span> <span className="font-mono">{done.email}</span></p>
            <p><span className="text-slate-500">Role:</span> {done.role}</p>
          </div>
          <button
            onClick={() => navigate("/login", { replace: true })}
            className="mt-6 w-full py-2.5 rounded-lg font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition"
          >
            Continue to sign in →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 flex flex-col">
      <header className="px-6 lg:px-12 py-5 flex items-center justify-between max-w-7xl mx-auto w-full">
        <Link to="/" className="flex items-center gap-3">
          <img src="/scheduler-logo.png" alt="logo" className="h-9 w-9 object-contain" />
          <span className="text-lg font-bold text-slate-900">ClassSync<span className="text-indigo-600">.</span></span>
        </Link>
        <Link to="/org-login" className="text-sm text-slate-600 hover:text-slate-900">Already registered? Sign in →</Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-slate-900">Register your school</h1>
            <p className="mt-1 text-sm text-slate-500">
              Create your organisation and primary management account. Teachers and students are added later by you.
            </p>
          </div>

          {error && (
            <div className="mb-5 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Organisation */}
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wide text-indigo-700 mb-3">School information</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <input
                    type="text"
                    value={org.name}
                    onChange={setO("name")}
                    onBlur={(e) => regenerateCode(e.target.value)}
                    placeholder="School name *"
                    required
                    className={`w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                      fieldErrors["name"] ? "border-red-400 bg-red-50" : "border-slate-300"
                    }`}
                  />
                  {fieldErrors["name"] && <p className="mt-1 text-xs text-red-600">{fieldErrors["name"]}</p>}
                </div>
                <div>
                  <div className="flex items-stretch gap-2">
                    <div className="flex-1 px-3 py-2 rounded-lg border border-slate-300 bg-slate-50 text-slate-700 font-mono text-sm flex items-center">
                      {org.school_code || "Generating…"}
                    </div>
                    <button
                      type="button"
                      onClick={() => regenerateCode(org.name)}
                      title="Generate a new code"
                      className="px-3 rounded-lg border border-indigo-300 text-indigo-700 text-sm hover:bg-indigo-50"
                    >
                      Regenerate
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Auto-generated unique school code</p>
                  {fieldErrors["school_code"] && <p className="mt-1 text-xs text-red-600">{fieldErrors["school_code"]}</p>}
                </div>
                <select value={org.board} onChange={setO("board")} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  {BOARDS.map((b) => <option key={b} value={b}>{b}</option>)}
                </select>
                {input(org.contact_number, setO("contact_number"), "Contact number")}
                {input(org.official_email, setO("official_email"), "Official email *", "official_email", "email", true)}
                {input(org.website, setO("website"), "Website (optional)")}
                {input(org.address, setO("address"), "Address")}
                {input(org.city, setO("city"), "City")}
                {input(org.state, setO("state"), "State")}
                {input(org.country, setO("country"), "Country")}
                {input(org.postal_code, setO("postal_code"), "Postal code")}
                {input(org.password, setO("password"), "Organisation password *", "org_password", "password", true)}
              </div>
            </section>

            {/* Primary account */}
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wide text-indigo-700 mb-3">Your account (primary admin)</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {input(admin.full_name, setA("full_name"), "Full name *", "full_name", "text", true)}
                <select value={admin.designation} onChange={setA("designation")} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  {DESIGNATIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
                {input(admin.email, setA("email"), "Your email *", "admin_email", "email", true)}
                {input(admin.phone, setA("phone"), "Phone number")}
                {input(admin.password, setA("password"), "Password *", "admin_password", "password", true)}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Only Owner / Admin / Principal accounts can self-register. Teachers, students and parents are created from your dashboard.
              </p>
            </section>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
                loading ? "bg-indigo-400 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700"
              }`}
            >
              {loading ? "Creating organisation…" : "Create organisation"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
