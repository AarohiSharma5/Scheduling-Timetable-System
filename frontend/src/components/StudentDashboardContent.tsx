import React, { useState, useEffect, useMemo } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";
import NotificationsCenter from "./NotificationsCenter";
import AnnouncementsPanel from "./AnnouncementsPanel";
import AssignmentsPanel from "./AssignmentsPanel";
import StudentFeesView from "./StudentFeesView";
import CalendarPanel from "./CalendarPanel";
import MessagesPanel from "./MessagesPanel";
import StudentServicesView from "./StudentServicesView";

interface PeriodRow {
  number: number;
  start: string;
  end: string;
  is_lunch?: boolean;
  is_short_break?: boolean;
  is_zero?: boolean;
}
interface SlotCell {
  period: number;
  subject: string;
  subject_id: number | null;
  teacher: string | null;
  teacher_id: number | null;
  room: string | null;
  is_lunch: boolean;
  is_short_break: boolean;
}
interface BatchSchedule {
  batch: { grade: string; section: string; student_count: number | null; display_name?: string };
  schedule: Record<string, SlotCell[]>;
  periods: PeriodRow[];
  days: string[];
  timetable_name: string;
  timetable_status: string;
  student_count: number | null;
  weekly_periods: number;
  subjects: { id: number; name: string }[];
  teachers: { id: number; name: string }[];
}

type Tab = "overview" | "schedule" | "teachers" | "subjects" | "homework" | "fees" | "services" | "calendar" | "messages" | "announcements" | "notifications";

export default function StudentDashboardContent() {
  const { user } = useAuthStore();
  const [data, setData] = useState<BatchSchedule | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const load = async () => {
      if (!user?.batch_id) {
        setError("Your account isn't linked to a class yet. Please contact the admin.");
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const res = await api.timetable.getBatchSchedule(user.batch_id);
        setData(res);
      } catch (e: any) {
        setError(e?.response?.data?.error || "Couldn't load your timetable. A timetable may not be generated yet.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [user?.batch_id]);

  const cellByDayPeriod = useMemo(() => {
    const m: Record<string, SlotCell> = {};
    if (data) {
      for (const day of Object.keys(data.schedule)) {
        for (const c of data.schedule[day]) m[`${day}|${c.period}`] = c;
      }
    }
    return m;
  }, [data]);

  const TabButton = ({ id, label }: { id: Tab; label: string }) => (
    <button
      onClick={() => { setActiveTab(id); setNotice(""); }}
      className={`px-4 py-2 rounded-lg font-medium transition ${
        activeTab === id ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700 hover:bg-slate-300"
      }`}
    >
      {label}
    </button>
  );

  const quickLink = (label: string, onClick: () => void) => (
    <button
      onClick={onClick}
      className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition"
    >
      {label}
    </button>
  );

  if (loading) return <p className="text-center py-10 text-slate-500">⏳ Loading your dashboard…</p>;
  if (error) return <div className="bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-lg">{error}</div>;
  if (!data) return null;

  const cls = data.batch.grade;
  const section = data.batch.section;
  const classmates = (data.student_count ?? data.batch.student_count ?? 0);

  return (
    <div className="space-y-6">
      <div className="flex gap-2 flex-wrap">
        <TabButton id="overview" label="📊 My Info" />
        <TabButton id="schedule" label="📅 My Timetable" />
        <TabButton id="teachers" label="👨‍🏫 My Teachers" />
        <TabButton id="subjects" label="📖 My Subjects" />
        <TabButton id="homework" label="📒 Homework" />
        <TabButton id="fees" label="💳 Fees" />
        <TabButton id="services" label="🚌 Services" />
        <TabButton id="calendar" label="🗓️ Calendar" />
        <TabButton id="messages" label="💬 Messages" />
        <TabButton id="announcements" label="📣 Announcements" />
        <TabButton id="notifications" label="🔔 Notifications" />
      </div>

      {notice && (
        <div className="bg-slate-100 border border-slate-300 text-slate-700 px-4 py-3 rounded-lg">{notice}</div>
      )}

      {/* Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
            <h2 className="text-2xl font-bold text-blue-900 mb-4">👋 Welcome, {user?.name}!</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4">
                <p className="text-2xl font-bold text-blue-600">{cls}</p>
                <p className="text-sm text-gray-600">Class</p>
              </div>
              <div className="bg-white rounded-lg p-4">
                <p className="text-2xl font-bold text-purple-600">{section}</p>
                <p className="text-sm text-gray-600">Section</p>
              </div>
              <div className="bg-white rounded-lg p-4">
                <p className="text-2xl font-bold text-green-600">{data.subjects.length}</p>
                <p className="text-sm text-gray-600">Subjects</p>
              </div>
              <div className="bg-white rounded-lg p-4">
                <p className="text-2xl font-bold text-orange-600">{classmates}</p>
                <p className="text-sm text-gray-600">Classmates</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
              <p className="text-3xl font-bold text-purple-600">{data.subjects.length}</p>
              <p className="text-gray-600 mt-2">Subjects</p>
              <p className="text-xs text-gray-500 mt-1">This term</p>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border-2 border-green-200">
              <p className="text-3xl font-bold text-green-600">{data.weekly_periods}</p>
              <p className="text-gray-600 mt-2">Weekly Classes</p>
              <p className="text-xs text-gray-500 mt-1">{data.days.length} days/week</p>
            </div>
            <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-lg p-6 border-2 border-pink-200">
              <p className="text-3xl font-bold text-pink-600">{data.teachers.length}</p>
              <p className="text-gray-600 mt-2">Teachers</p>
              <p className="text-xs text-gray-500 mt-1">Across your subjects</p>
            </div>
          </div>

          <div className="bg-gradient-to-r from-cyan-50 to-cyan-100 rounded-lg p-6 border-2 border-cyan-200">
            <h3 className="font-bold text-cyan-900 mb-4">📌 Quick Links</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {quickLink("📅 My Timetable", () => setActiveTab("schedule"))}
              {quickLink("👨‍🏫 Teachers", () => setActiveTab("teachers"))}
              {quickLink("📖 Subjects", () => setActiveTab("subjects"))}
              {quickLink("🔔 Notifications", () => setActiveTab("notifications"))}
              {quickLink("📝 Assignments", () => setNotice("Assignments aren't available yet — this feature is coming soon."))}
              {quickLink("🏆 My Grades", () => setNotice("Grades aren't available yet — this feature is coming soon."))}
            </div>
          </div>
        </div>
      )}

      {/* Timetable */}
      {activeTab === "schedule" && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm overflow-x-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-gray-900">📅 {cls}-{section} Weekly Timetable</h3>
            <span className="text-xs text-slate-400">
              {data.timetable_name} · {data.timetable_status}
            </span>
          </div>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border bg-slate-100 px-2 py-2 text-left w-28">Period</th>
                {data.days.map((d) => (
                  <th key={d} className="border bg-slate-100 px-2 py-2 text-left">{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.periods.map((p) => (
                <tr key={p.number}>
                  <td className="border bg-slate-50 px-2 py-2 align-top">
                    <div className="font-medium text-slate-700">
                      {p.is_zero ? "Zero" : `P${p.number}`}
                    </div>
                    <div className="text-[11px] text-slate-400">{p.start}–{p.end}</div>
                  </td>
                  {data.days.map((day) => {
                    const c = cellByDayPeriod[`${day}|${p.number}`];
                    if (p.is_lunch || c?.is_lunch) {
                      return <td key={day} className="border px-2 py-3 text-center text-amber-700 bg-amber-50 font-medium">Lunch</td>;
                    }
                    if (p.is_short_break || c?.is_short_break) {
                      return <td key={day} className="border px-2 py-3 text-center text-green-700 bg-green-50 font-medium">Break</td>;
                    }
                    if (!c) {
                      return <td key={day} className="border px-2 py-3 text-center text-slate-300">—</td>;
                    }
                    return (
                      <td key={day} className="border px-2 py-2 bg-blue-50">
                        <div className="font-semibold text-slate-900">{c.subject}</div>
                        <div className="text-xs text-slate-600">{c.teacher || ""}</div>
                        {c.room && <div className="text-[11px] text-slate-400">{c.room}</div>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Teachers */}
      {activeTab === "teachers" && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 className="font-bold text-gray-900 mb-4">👨‍🏫 My Teachers</h3>
          {data.teachers.length === 0 ? (
            <p className="text-slate-500">No teachers found in your timetable yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.teachers.map((t) => (
                <div key={t.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 font-medium text-slate-800">
                  {t.name}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Subjects */}
      {activeTab === "subjects" && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 className="font-bold text-gray-900 mb-4">📖 My Subjects</h3>
          {data.subjects.length === 0 ? (
            <p className="text-slate-500">No subjects found in your timetable yet.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {data.subjects.map((s) => (
                <div key={s.id} className="p-3 bg-indigo-50 rounded-lg border border-indigo-200 font-medium text-indigo-900">
                  {s.name}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "homework" && <AssignmentsPanel />}

      {activeTab === "fees" && <StudentFeesView />}

      {activeTab === "services" && <StudentServicesView />}

      {activeTab === "calendar" && <CalendarPanel />}

      {activeTab === "messages" && <MessagesPanel />}

      {activeTab === "announcements" && <AnnouncementsPanel />}

      {activeTab === "notifications" && <NotificationsCenter />}
    </div>
  );
}
