import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useOrgStore } from "../stores/orgStore";

// Demo credentials are only useful against a seeded dev database.
const SHOW_DEMO = process.env.NODE_ENV !== "production";

const modules = [
  { icon: "📅", title: "Timetabling", desc: "Conflict-free schedules for every class & teacher, generated asynchronously so it scales without request timeouts." },
  { icon: "✅", title: "Attendance", desc: "Daily and period-wise marking with instant defaulter and percentage reporting." },
  { icon: "🧪", title: "Exams & Gradebook", desc: "Assessments, marks entry, weighted grades and printable report cards." },
  { icon: "💳", title: "Fees & Payments", desc: "Fee structures, invoicing, payment tracking and outstanding-dues summaries." },
  { icon: "📒", title: "Homework", desc: "Assignment creation, student submission and teacher grading in one flow." },
  { icon: "📣", title: "Parent Comms", desc: "Targeted announcements and direct messaging that keep guardians in the loop." },
  { icon: "🗓️", title: "Calendar & Library", desc: "Academic calendar, holidays, book catalogue and issue/return tracking." },
  { icon: "🚌", title: "Transport & Inventory", desc: "Routes, stop assignments, capacity checks and stock management." },
  { icon: "📈", title: "Analytics", desc: "School-wide KPIs across attendance, fees, exams and operations." },
];

const security = [
  { icon: "🛡️", title: "Tenant isolation", desc: "Every query is scoped to your organization. One school can never see another's data." },
  { icon: "🔐", title: "PII encrypted at rest", desc: "Student personal data is encrypted with AES (Fernet) before it touches the database." },
  { icon: "⚖️", title: "DPDP / GDPR ready", desc: "Consent tracking, data-subject export, right-to-erasure and a full audit trail." },
  { icon: "💾", title: "Backups & restore", desc: "Scripted, scheduled, encrypted database dumps with a tested restore path." },
];

const stats = [
  { value: "200 → 20,000+", label: "students per school" },
  { value: "Encrypted", label: "PII at rest" },
  { value: "Multi-tenant", label: "isolated by org" },
  { value: "Async", label: "generation at scale" },
];

export default function LandingPage() {
  const { organization } = useOrgStore();
  const navigate = useNavigate();

  const handleOrgCta = () => {
    navigate(organization ? "/login" : "/org-login");
  };

  const ctaLabel = organization ? "Continue to login →" : "Get started →";

  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* Announcement bar */}
      <div className="bg-slate-900 text-slate-200 text-center text-xs sm:text-sm py-2 px-4">
        The complete operating system for modern schools — timetabling, academics, fees, and communication in one secure platform.
      </div>

      {/* Top Nav */}
      <header className="sticky top-0 z-30 backdrop-blur bg-white/80 border-b border-slate-200">
        <div className="px-6 lg:px-12 py-4 flex items-center justify-between max-w-7xl mx-auto">
          <Link to="/" className="flex items-center gap-3">
            <img src="/scheduler-logo.png" alt="ClassSync logo" className="h-9 w-9 object-contain" />
            <span className="text-xl font-bold tracking-tight text-slate-900">
              ClassSync<span className="text-indigo-600">.</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <a href="#modules" className="hover:text-slate-900 transition">Platform</a>
            <a href="#security" className="hover:text-slate-900 transition">Security</a>
            <a href="#scale" className="hover:text-slate-900 transition">Scale</a>
          </nav>

          <div className="flex items-center gap-3">
            {organization && (
              <span className="hidden sm:inline text-sm text-slate-500">
                {organization.name}
              </span>
            )}
            <button
              onClick={handleOrgCta}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold shadow-sm hover:bg-indigo-700 transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              {organization ? "Continue to login" : "Sign in"}
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 -right-32 h-96 w-96 rounded-full bg-indigo-200/50 blur-3xl" />
          <div className="absolute top-40 -left-32 h-96 w-96 rounded-full bg-cyan-200/40 blur-3xl" />
        </div>

        <div className="relative px-6 lg:px-12 max-w-7xl mx-auto pt-16 pb-20 grid lg:grid-cols-2 gap-14 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-semibold uppercase tracking-wide ring-1 ring-indigo-100">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
              School management platform
            </span>
            <h1 className="mt-5 text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.05]">
              Run your entire school on{" "}
              <span className="bg-gradient-to-r from-indigo-600 to-cyan-600 bg-clip-text text-transparent">
                one secure platform
              </span>
              .
            </h1>
            <p className="mt-6 text-lg text-slate-600 max-w-xl">
              ClassSync brings timetabling, attendance, exams, fees, homework and parent
              communication together — built multi-tenant and encrypted, so it handles any
              school's data, from a few hundred to tens of thousands of students.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleOrgCta}
                className="px-6 py-3 rounded-lg bg-indigo-600 text-white font-semibold shadow-md hover:bg-indigo-700 transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                {ctaLabel}
              </button>
              <a
                href="#modules"
                className="px-6 py-3 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold hover:bg-slate-50 transition text-center"
              >
                Explore the platform
              </a>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-500">
              <span className="flex items-center gap-2"><span className="text-emerald-500">●</span> Encrypted PII at rest</span>
              <span className="flex items-center gap-2"><span className="text-emerald-500">●</span> Per-school data isolation</span>
              <span className="flex items-center gap-2"><span className="text-emerald-500">●</span> Audit trail & backups</span>
            </div>

            {SHOW_DEMO && !organization && (
              <p className="mt-6 text-xs text-slate-400">
                Dev demo →{" "}
                <span className="font-mono text-slate-500">Test Sample Institute</span>{" "}
                / <span className="font-mono text-slate-500">institute123</span>
              </p>
            )}
          </div>

          {/* Product preview */}
          <div className="relative">
            <div className="absolute -inset-6 bg-gradient-to-tr from-indigo-200 via-cyan-100 to-transparent blur-2xl rounded-full opacity-70" />
            <div className="relative bg-white rounded-2xl shadow-2xl ring-1 ring-slate-200 overflow-hidden">
              {/* window chrome */}
              <div className="flex items-center gap-1.5 px-4 py-3 border-b border-slate-100 bg-slate-50">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="ml-3 text-xs text-slate-400">Admin dashboard</span>
              </div>
              <div className="p-5">
                {/* stat tiles */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { k: "Students", v: "2,847", c: "from-indigo-500 to-indigo-600" },
                    { k: "Attendance", v: "96.4%", c: "from-emerald-500 to-emerald-600" },
                    { k: "Fees due", v: "₹4.2L", c: "from-amber-500 to-amber-600" },
                  ].map((t) => (
                    <div key={t.k} className="rounded-xl border border-slate-100 p-3">
                      <div className={`h-1.5 w-8 rounded-full bg-gradient-to-r ${t.c} mb-2`} />
                      <p className="text-lg font-bold text-slate-800">{t.v}</p>
                      <p className="text-[11px] text-slate-400">{t.k}</p>
                    </div>
                  ))}
                </div>

                {/* mini timetable grid */}
                <div className="mt-4 rounded-xl border border-slate-100 p-3">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2">Weekly timetable</p>
                  <div className="grid grid-cols-6 gap-1.5">
                    {Array.from({ length: 30 }).map((_, i) => {
                      const palette = [
                        "bg-indigo-100",
                        "bg-cyan-100",
                        "bg-emerald-100",
                        "bg-amber-100",
                        "bg-rose-100",
                        "bg-slate-100",
                      ];
                      return (
                        <div
                          key={i}
                          className={`h-6 rounded ${palette[(i * 7) % palette.length]}`}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stat band */}
      <section className="border-y border-slate-200 bg-slate-50">
        <div className="px-6 lg:px-12 max-w-7xl mx-auto py-10 grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-2xl md:text-3xl font-extrabold text-slate-900">{s.value}</p>
              <p className="mt-1 text-sm text-slate-500">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Modules */}
      <section id="modules" className="px-6 lg:px-12 max-w-7xl mx-auto py-24">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold">One platform, every school workflow</h2>
          <p className="mt-4 text-slate-600">
            Replace a patchwork of spreadsheets and disconnected tools with a single,
            role-aware system for administrators, teachers, students and parents.
          </p>
        </div>

        <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((m) => (
            <div
              key={m.title}
              className="group bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-xl hover:-translate-y-1 hover:border-indigo-200 transition"
            >
              <div className="text-3xl">{m.icon}</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">{m.title}</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Security & compliance */}
      <section id="security" className="bg-slate-900 text-white">
        <div className="px-6 lg:px-12 max-w-7xl mx-auto py-24">
          <div className="grid lg:grid-cols-2 gap-14 items-start">
            <div>
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-indigo-200 text-xs font-semibold uppercase tracking-wide">
                Security & compliance
              </span>
              <h2 className="mt-5 text-3xl md:text-4xl font-bold leading-tight">
                Built to be trusted with minors' data
              </h2>
              <p className="mt-5 text-slate-300 max-w-lg">
                Schools are legally responsible for student data. ClassSync is engineered
                for that responsibility from the ground up — not bolted on later — so it can
                safely hold any school's database.
              </p>
              <button
                onClick={handleOrgCta}
                className="mt-8 px-6 py-3 rounded-lg bg-white text-slate-900 font-semibold hover:bg-slate-100 transition"
              >
                {ctaLabel}
              </button>
            </div>

            <div className="grid sm:grid-cols-2 gap-5">
              {security.map((s) => (
                <div key={s.title} className="rounded-2xl bg-white/[0.06] border border-white/10 p-5">
                  <div className="text-2xl">{s.icon}</div>
                  <h3 className="mt-3 font-semibold text-white">{s.title}</h3>
                  <p className="mt-1.5 text-sm text-slate-300 leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Scale */}
      <section id="scale" className="px-6 lg:px-12 max-w-7xl mx-auto py-24">
        <div className="grid lg:grid-cols-2 gap-14 items-center">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold">Engineered to scale with you</h2>
            <p className="mt-5 text-slate-600 max-w-lg">
              Whether you onboard one school or an entire district, the architecture holds up:
              each institute is its own isolated tenant, heavy work runs on a background queue,
              and large lists are paginated and indexed.
            </p>
            <ul className="mt-8 space-y-4">
              {[
                ["Multi-tenant by design", "Add unlimited schools — data stays cleanly separated per organization."],
                ["No request timeouts", "Timetable generation runs on a background worker and reports progress."],
                ["Operational readiness", "Liveness/readiness health checks, structured audit logs and DB backups."],
              ].map(([t, d]) => (
                <li key={t} className="flex gap-3">
                  <span className="mt-1 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-emerald-100 text-emerald-600 text-sm font-bold">✓</span>
                  <div>
                    <p className="font-semibold text-slate-900">{t}</p>
                    <p className="text-sm text-slate-600">{d}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-indigo-50 to-cyan-50 border border-slate-200 p-8">
            <div className="grid grid-cols-2 gap-6">
              {[
                ["∞", "Schools (tenants)"],
                ["20k+", "Students per school"],
                ["100%", "Org-scoped queries"],
                ["AES", "PII encryption"],
              ].map(([v, l]) => (
                <div key={l} className="text-center">
                  <p className="text-3xl font-extrabold bg-gradient-to-r from-indigo-600 to-cyan-600 bg-clip-text text-transparent">{v}</p>
                  <p className="mt-1 text-sm text-slate-500">{l}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA strip */}
      <section className="px-6 lg:px-12 pb-24">
        <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-r from-indigo-600 to-cyan-600 text-white p-10 md:p-14 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl">
          <div>
            <h3 className="text-2xl md:text-3xl font-bold">Bring your whole school online</h3>
            <p className="mt-2 text-indigo-100">
              Sign in to your organisation to reach the role-based dashboards.
            </p>
          </div>
          <button
            onClick={handleOrgCta}
            className="px-7 py-3 rounded-lg bg-white text-indigo-700 font-semibold hover:bg-indigo-50 transition focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-600 whitespace-nowrap"
          >
            {ctaLabel}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200">
        <div className="px-6 lg:px-12 py-10 max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <img src="/scheduler-logo.png" alt="logo" className="h-6 w-6" />
            <span>ClassSync &copy; {new Date().getFullYear()} — School management platform</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#modules" className="hover:text-slate-700">Platform</a>
            <a href="#security" className="hover:text-slate-700">Security</a>
            <Link to="/org-login" className="hover:text-slate-700">Organisation login</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
