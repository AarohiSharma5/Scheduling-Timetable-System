import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";
import AnnouncementsPanel from "./AnnouncementsPanel";
import NotificationsCenter from "./NotificationsCenter";
import StudentFeesView from "./StudentFeesView";
import StudentAssignmentsView from "./StudentAssignmentsView";

interface Child {
  student_id: number;
  name: string;
  class: string;
  roll_no: number | null;
}

interface AttendanceData {
  summary: { present: number; absent: number; late: number; excused: number; total: number; percentage: number | null };
  records: { id: number; date: string; status: string }[];
}

interface ExamResult {
  exam: { id: number; name: string; status: string };
  subjects: { subject: string; marks_obtained: number | null; max_marks: number; is_absent: boolean; grade: string | null }[];
  total_obtained: number;
  total_max: number;
  percentage: number | null;
  overall_grade: string | null;
}

type Tab = "attendance" | "results" | "homework" | "fees" | "announcements" | "notifications";

const gradeColor = (g: string | null) => {
  if (!g) return "text-slate-400";
  if (g.startsWith("A")) return "text-green-700";
  if (g.startsWith("B")) return "text-emerald-600";
  if (g.startsWith("C")) return "text-amber-600";
  if (g === "D") return "text-orange-600";
  return "text-red-600";
};

export default function ParentDashboardContent() {
  const { user } = useAuthStore();
  const [children, setChildren] = useState<Child[]>([]);
  const [activeChild, setActiveChild] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("attendance");
  const [attendance, setAttendance] = useState<AttendanceData | null>(null);
  const [results, setResults] = useState<ExamResult[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const kids = await api.parents.children();
        setChildren(kids);
        if (kids.length) setActiveChild(kids[0].student_id);
        else setErr("No children are linked to your account yet. Please contact the school admin.");
      } catch (e: any) {
        setErr(e?.response?.data?.error || "Couldn't load your children.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (activeChild == null) return;
    if (tab === "attendance") {
      api.attendance.student(activeChild).then(setAttendance).catch(() => setAttendance(null));
    } else if (tab === "results") {
      api.exams.student(activeChild).then((d) => setResults(d.results)).catch(() => setResults(null));
    }
  }, [activeChild, tab]);

  if (loading) return <p className="text-center py-10 text-slate-500">⏳ Loading…</p>;

  const child = children.find((c) => c.student_id === activeChild);

  const TabBtn = ({ id, label }: { id: Tab; label: string }) => (
    <button
      onClick={() => setTab(id)}
      className={`px-4 py-2 rounded-lg font-medium transition ${
        tab === id ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700 hover:bg-slate-300"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-lg p-6 border-2 border-amber-200">
        <h2 className="text-2xl font-bold text-amber-900">👋 Welcome, {user?.name}!</h2>
        <p className="text-amber-800 mt-1">Track your children's attendance, results, and school news.</p>
      </div>

      {err && <div className="bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-lg">{err}</div>}

      {children.length > 0 && (
        <>
          {/* Child selector */}
          {children.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {children.map((c) => (
                <button
                  key={c.student_id}
                  onClick={() => setActiveChild(c.student_id)}
                  className={`px-4 py-2 rounded-lg border font-medium ${
                    activeChild === c.student_id
                      ? "bg-white border-blue-500 text-blue-700"
                      : "bg-slate-50 border-slate-200 text-slate-600"
                  }`}
                >
                  {c.name} <span className="text-xs text-slate-400">({c.class})</span>
                </button>
              ))}
            </div>
          )}

          {child && (
            <p className="text-sm text-slate-500">
              Showing <span className="font-semibold text-slate-700">{child.name}</span> · Class {child.class}
              {child.roll_no ? ` · Roll ${child.roll_no}` : ""}
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <TabBtn id="attendance" label="📝 Attendance" />
            <TabBtn id="results" label="🧾 Results" />
            <TabBtn id="homework" label="📒 Homework" />
            <TabBtn id="fees" label="💳 Fees" />
            <TabBtn id="announcements" label="📣 Announcements" />
            <TabBtn id="notifications" label="🔔 Notifications" />
          </div>

          {tab === "attendance" && (
            attendance ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <Stat label="Attendance" value={attendance.summary.percentage == null ? "—" : `${attendance.summary.percentage}%`} accent="text-blue-600" />
                  <Stat label="Present" value={attendance.summary.present} accent="text-green-600" />
                  <Stat label="Absent" value={attendance.summary.absent} accent="text-red-600" />
                  <Stat label="Late" value={attendance.summary.late} accent="text-amber-600" />
                  <Stat label="Days recorded" value={attendance.summary.total} accent="text-slate-700" />
                </div>
                <div className="border border-slate-200 rounded-lg divide-y max-h-80 overflow-y-auto">
                  {attendance.records.length === 0 ? (
                    <p className="text-slate-500 text-sm p-3">No attendance recorded yet.</p>
                  ) : attendance.records.map((r) => (
                    <div key={r.id} className="flex justify-between px-3 py-2 text-sm">
                      <span className="text-slate-600">{new Date(r.date).toLocaleDateString()}</span>
                      <span className={`font-medium capitalize ${
                        r.status === "present" ? "text-green-700"
                          : r.status === "absent" ? "text-red-600"
                          : r.status === "late" ? "text-amber-600" : "text-slate-600"
                      }`}>{r.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <p className="text-slate-500 text-sm">No attendance available yet.</p>
          )}

          {tab === "results" && (
            results && results.length > 0 ? (
              <div className="space-y-4">
                {results.map((r) => (
                  <div key={r.exam.id} className="border border-slate-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-slate-800">{r.exam.name}</h4>
                      <span className="text-sm">
                        <span className="font-bold">{r.percentage == null ? "—" : `${r.percentage}%`}</span>
                        <span className={`ml-2 font-bold ${gradeColor(r.overall_grade)}`}>{r.overall_grade ?? ""}</span>
                      </span>
                    </div>
                    <table className="w-full text-sm">
                      <tbody>
                        {r.subjects.map((s, i) => (
                          <tr key={i} className="border-t">
                            <td className="py-1.5 text-slate-700">{s.subject}</td>
                            <td className="py-1.5 text-right">
                              {s.is_absent ? <span className="text-red-600">Absent</span> : `${s.marks_obtained}/${s.max_marks}`}
                            </td>
                            <td className={`py-1.5 text-right w-12 font-semibold ${gradeColor(s.grade)}`}>{s.grade ?? ""}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            ) : <p className="text-slate-500 text-sm">No published results yet.</p>
          )}

          {tab === "homework" && activeChild != null && <StudentAssignmentsView studentId={activeChild} />}
          {tab === "fees" && activeChild != null && <StudentFeesView studentId={activeChild} />}
          {tab === "announcements" && <AnnouncementsPanel />}
          {tab === "notifications" && <NotificationsCenter />}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: React.ReactNode; accent: string }) {
  return (
    <div className="bg-white rounded-lg p-4 border border-slate-200 text-center">
      <p className={`text-2xl font-bold ${accent}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}
