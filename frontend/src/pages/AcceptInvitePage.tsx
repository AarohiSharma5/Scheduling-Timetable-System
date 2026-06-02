import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { api } from "../api";

const pwOk = (pw: string) => /^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(pw);

export default function AcceptInvitePage() {
  const { token = "" } = useParams();
  const navigate = useNavigate();

  const [checking, setChecking] = useState(true);
  const [valid, setValid] = useState(false);
  const [info, setInfo] = useState<{ email?: string; name?: string; role?: string; organization?: string }>({});
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.invitations.info(token);
        setValid(!!res.valid);
        setInfo(res);
        setName(res.name || "");
      } catch (err: any) {
        setError(err?.response?.data?.error || "This invitation is invalid or expired.");
      } finally {
        setChecking(false);
      }
    })();
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Please enter your name.");
      return;
    }
    if (!pwOk(password)) {
      setError("Password must be at least 8 characters and include a letter and a number.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await api.invitations.accept(token, { name: name.trim(), password, phone: phone.trim() });
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.error || "Could not create your account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white/[0.06] backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 p-8">
        <h1 className="text-2xl font-bold text-white mb-1">Accept invitation</h1>

        {checking ? (
          <p className="text-slate-300 text-sm mt-4">Checking invitation…</p>
        ) : done ? (
          <div className="mt-4 space-y-4">
            <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-100 text-sm">
              Your account is ready. Sign in with your email and new password.
            </div>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="w-full py-2.5 rounded-lg font-semibold text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Go to sign in
            </button>
          </div>
        ) : !valid ? (
          <div className="mt-4 p-3 rounded-lg bg-red-500/20 border border-red-500 text-red-200 text-sm">
            {error || "This invitation is invalid or expired."}
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-300 mb-6">
              {info.organization ? <>Join <span className="font-semibold text-white">{info.organization}</span> as </> : "Join as "}
              <span className="capitalize font-semibold text-indigo-300">{info.role}</span>
              {info.email ? <> · {info.email}</> : null}
            </p>
            {error && (
              <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">{error}</div>
            )}
            <form onSubmit={submit} className="space-y-4">
              <Field label="Full name" type="text" value={name} onChange={setName} />
              <Field label="Phone (optional)" type="text" value={phone} onChange={setPhone} />
              <Field label="Create password" type="password" value={password} onChange={setPassword} />
              <Field label="Confirm password" type="password" value={confirm} onChange={setConfirm} />
              <button
                type="submit"
                disabled={loading}
                className={`w-full py-2.5 rounded-lg font-semibold text-white transition ${
                  loading ? "bg-slate-600 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700"
                }`}
              >
                {loading ? "Creating…" : "Create my account"}
              </button>
            </form>
          </>
        )}

        <div className="mt-6 text-center">
          <Link to="/" className="text-sm text-slate-300 hover:text-white">← Home</Link>
        </div>
      </div>
    </div>
  );
}

function Field({
  label, type, value, onChange,
}: { label: string; type: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-medium text-white mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 rounded-lg bg-slate-900/50 border border-white/10 text-white placeholder-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none transition"
      />
    </div>
  );
}
