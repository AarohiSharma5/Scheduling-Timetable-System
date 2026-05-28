import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useOrgStore } from "../stores/orgStore";

const features = [
  {
    icon: "📅",
    title: "Automated Timetables",
    desc: "Generate conflict-free schedules for every batch in seconds, with smart distribution across periods and days.",
  },
  {
    icon: "🧠",
    title: "Conflict Detection",
    desc: "Catch teacher double-bookings, batch overlaps, and subject gaps before publishing.",
  },
  {
    icon: "🤝",
    title: "Leave & Substitution",
    desc: "Teachers request leave, admins approve, and substitutes auto-fill affected periods — notifications included.",
  },
  {
    icon: "🧾",
    title: "PDF Export",
    desc: "Professional A4 timetables for any batch or teacher — branded with your organization name.",
  },
  {
    icon: "🔐",
    title: "Role-based Access",
    desc: "Distinct dashboards for Admin, Principal, Coordinator, Teacher, and Student.",
  },
  {
    icon: "🏫",
    title: "Multi-organization",
    desc: "Every institute logs in to its own tenant — your data stays scoped to your organization.",
  },
];

export default function LandingPage() {
  const { organization } = useOrgStore();
  const navigate = useNavigate();

  const handleOrgCta = () => {
    if (organization) {
      navigate("/login");
    } else {
      navigate("/org-login");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 text-slate-900">
      {/* Top Nav */}
      <header className="px-6 lg:px-12 py-5 flex items-center justify-between max-w-7xl mx-auto">
        <Link to="/" className="flex items-center gap-3">
          <img
            src="/scheduler-logo.png"
            alt="Scheduler logo"
            className="h-10 w-10 object-contain"
          />
          <span className="text-xl font-bold tracking-tight text-slate-900">
            ClassSync<span className="text-indigo-600">.</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          {organization && (
            <span className="hidden sm:inline text-sm text-slate-500">
              Signed in as{" "}
              <span className="font-medium text-slate-700">
                {organization.name}
              </span>
            </span>
          )}
          <button
            onClick={handleOrgCta}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold shadow-sm hover:bg-indigo-700 transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            {organization ? "Continue to user login →" : "Login as Organisation"}
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="px-6 lg:px-12 max-w-7xl mx-auto pt-10 pb-20 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold uppercase tracking-wide">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
            School Timetable Scheduler
          </span>
          <h1 className="mt-5 text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.1]">
            Build a perfect weekly schedule for your <span className="text-indigo-600">entire school</span> — in minutes.
          </h1>
          <p className="mt-6 text-lg text-slate-600 max-w-xl">
            ClassSync helps administrators generate, validate and publish timetables for
            every class and teacher, manage leaves and substitutions, and keep everyone
            in sync — all from a single dashboard.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleOrgCta}
              className="px-6 py-3 rounded-lg bg-indigo-600 text-white font-semibold shadow-md hover:bg-indigo-700 transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              {organization ? "Continue to user login →" : "Login as Organisation"}
            </button>
            <a
              href="#features"
              className="px-6 py-3 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold hover:bg-slate-50 transition text-center"
            >
              Explore features
            </a>
          </div>

          {!organization && (
            <p className="mt-6 text-sm text-slate-500">
              Try the demo organization →{" "}
              <span className="font-mono font-semibold text-slate-700">
                Test Sample Institute
              </span>{" "}
              / password{" "}
              <span className="font-mono font-semibold text-slate-700">institute123</span>
            </p>
          )}
        </div>

        {/* Logo card */}
        <div className="flex justify-center">
          <div className="relative">
            <div className="absolute -inset-6 bg-gradient-to-tr from-indigo-200 via-cyan-100 to-transparent blur-2xl rounded-full opacity-70" />
            <div className="relative bg-white rounded-3xl shadow-xl border border-slate-200 p-10 max-w-md">
              <img
                src="/scheduler-logo.png"
                alt="Scheduler logo"
                className="w-64 h-64 mx-auto object-contain"
              />
              <div className="mt-6 text-center">
                <p className="text-sm uppercase tracking-widest text-slate-400 font-semibold">
                  Built for institutes
                </p>
                <p className="mt-2 text-xl font-bold text-slate-800">
                  2,800+ students · 75 teachers · 14 classrooms
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  Pre-loaded demo dataset ready to explore.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 lg:px-12 max-w-7xl mx-auto pb-24">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900">
            Everything an institute needs in one place
          </h2>
          <p className="mt-4 text-slate-600">
            Generate, review, publish, and keep your timetables alive. Built for
            multi-grade schools and configurable to your school's hours, lunch breaks,
            and subject load.
          </p>
        </div>

        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-lg hover:-translate-y-0.5 transition"
            >
              <div className="text-3xl">{f.icon}</div>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">
                {f.title}
              </h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA strip */}
      <section className="px-6 lg:px-12 pb-24">
        <div className="max-w-5xl mx-auto rounded-2xl bg-gradient-to-r from-indigo-600 to-cyan-600 text-white p-10 flex flex-col md:flex-row items-center justify-between gap-6 shadow-lg">
          <div>
            <h3 className="text-2xl font-bold">Ready to start?</h3>
            <p className="mt-2 text-indigo-100">
              Log in as your organisation to access the role-based dashboards.
            </p>
          </div>
          <button
            onClick={handleOrgCta}
            className="px-6 py-3 rounded-lg bg-white text-indigo-700 font-semibold hover:bg-indigo-50 transition focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-600"
          >
            {organization ? "Continue to user login →" : "Login as Organisation →"}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 lg:px-12 py-8 border-t border-slate-200 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <img src="/scheduler-logo.png" alt="logo" className="h-6 w-6" />
            <span>
              ClassSync &copy; {new Date().getFullYear()} — School Timetable Scheduler
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a href="#features" className="hover:text-slate-700">
              Features
            </a>
            <Link to="/org-login" className="hover:text-slate-700">
              Organisation login
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
