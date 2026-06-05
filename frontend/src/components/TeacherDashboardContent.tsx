import React, { useState, useEffect, useMemo } from "react";
import { api } from "../api";
import NotificationsCenter from "./NotificationsCenter";
import StudentManagement from "./StudentManagement";
import AttendancePanel from "./AttendancePanel";
import ExamsPanel from "./ExamsPanel";
import AnnouncementsPanel from "./AnnouncementsPanel";
import AssignmentsPanel from "./AssignmentsPanel";
import CalendarPanel from "./CalendarPanel";
import LibraryPanel from "./LibraryPanel";
import MessagesPanel from "./MessagesPanel";
import { useAuthStore } from "../stores/authStore";

interface PeriodRow {
  number: number; start: string; end: string;
  is_lunch?: boolean; is_short_break?: boolean; is_zero?: boolean;
}
interface TeacherSlot { period: number; subject: string; class: string; room: string | null; }
interface TeacherSchedule {
  teacher: { id: number; name: string; is_class_teacher: boolean };
  schedule: Record<string, TeacherSlot[]>;
  periods: PeriodRow[];
  days: string[];
  timetable_name: string;
  timetable_status: string;
  stats: { classes: number; subjects: number; students: number; weekly_periods: number };
  classes: string[];
  subjects: { id: number; name: string }[];
}

type Tab = "overview" | "schedule" | "attendance" | "exams" | "homework" | "announcements" | "messages" | "calendar" | "library" | "myclass" | "notifications";

export default function TeacherDashboardContent() {
  const { user } = useAuthStore();
  const getCurrentUser = useAuthStore((s) => s.getCurrentUser);
  const [data, setData] = useState<TeacherSchedule | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showLeave, setShowLeave] = useState(false);

  const isClassTeacher = !!user?.is_class_teacher && !!user?.class_teacher_grade;

  // teacher_id is only populated by /auth/me, not the login response.
  useEffect(() => {
    if (user && !user.teacher_id) getCurrentUser();
  }, [user, getCurrentUser]);

  useEffect(() => {
    const load = async () => {
      if (!user?.teacher_id) return;
      try {
        setLoading(true);
        const res = await api.timetable.getTeacherSchedule(user.teacher_id);
        setData(res);
      } catch (e: any) {
        setError(e?.response?.data?.error || "Couldn't load your schedule. A timetable may not be generated yet.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [user?.teacher_id]);

  const cellByDayPeriod = useMemo(() => {
    const m: Record<string, TeacherSlot> = {};
    if (data) for (const d of Object.keys(data.schedule)) for (const c of data.schedule[d]) m[`${d}|${c.period}`] = c;
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

  const action = (label: string, onClick: () => void) => (
    <button onClick={onClick}
      className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex gap-2 flex-wrap">
        <TabButton id="overview" label="📊 My Schedule" />
        <TabButton id="schedule" label="📅 Timetable" />
        <TabButton id="attendance" label="📝 Attendance" />
        <TabButton id="exams" label="🧪 Exams" />
        <TabButton id="homework" label="📒 Homework" />
        <TabButton id="announcements" label="📣 Announcements" />
        <TabButton id="messages" label="💬 Messages" />
        <TabButton id="calendar" label="🗓️ Calendar" />
        <TabButton id="library" label="📚 Library" />
        {isClassTeacher && <TabButton id="myclass" label="🧑‍🎓 My Class" />}
        <TabButton id="notifications" label="🔔 Notifications" />
      </div>

      {notice && <div className="bg-slate-100 border border-slate-300 text-slate-700 px-4 py-3 rounded-lg">{notice}</div>}
      {error && <div className="bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-lg">{error}</div>}

      {activeTab === "overview" && (
        <div className="space-y-6">
          {loading ? (
            <p className="text-center py-8 text-slate-500">⏳ Loading dashboard…</p>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
                  <p className="text-3xl font-bold text-blue-600">{data?.stats.classes ?? 0}</p>
                  <p className="text-gray-600 mt-2">Classes Assigned</p>
                  <p className="text-xs text-gray-500 mt-1">Different grades/sections</p>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
                  <p className="text-3xl font-bold text-purple-600">{data?.stats.students ?? 0}</p>
                  <p className="text-gray-600 mt-2">Total Students</p>
                  <p className="text-xs text-gray-500 mt-1">Across your classes</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border-2 border-green-200">
                  <p className="text-3xl font-bold text-green-600">{data?.stats.subjects ?? 0}</p>
                  <p className="text-gray-600 mt-2">Subject(s) Taught</p>
                  <p className="text-xs text-gray-500 mt-1">From your timetable</p>
                </div>
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-6 border-2 border-orange-200">
                  <p className="text-3xl font-bold text-orange-600">{data?.stats.weekly_periods ?? 0}</p>
                  <p className="text-gray-600 mt-2">Weekly Periods</p>
                  <p className="text-xs text-gray-500 mt-1">Teaching load</p>
                </div>
              </div>

              <div className="bg-gradient-to-r from-cyan-50 to-cyan-100 rounded-lg p-6 border-2 border-cyan-200">
                <h3 className="font-bold text-cyan-900 mb-4">📌 Quick Actions</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {action("📊 My Timetable", () => setActiveTab("schedule"))}
                  {action("📚 My Classes", () => setNotice(
                    data && data.classes.length ? `You teach: ${data.classes.join(", ")}` : "No classes found in the current timetable."))}
                  {action("📋 Request Leave", () => setShowLeave(true))}
                  {action("🔔 Notifications", () => setActiveTab("notifications"))}
                  {action("📝 Mark Attendance", () => setActiveTab("attendance"))}
                  {action("🎓 View Profile", () => setNotice(
                    `${data?.teacher.name || user?.name}${data ? ` · ${data.stats.subjects} subject(s), ${data.stats.classes} class(es)` : ""}`))}
                </div>
              </div>

              <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
                <h3 className="font-bold text-gray-900 mb-4">📅 This Week's Schedule</h3>
                {!data || Object.keys(data.schedule).length === 0 ? (
                  <p className="text-slate-500 text-sm">No classes scheduled in the current timetable.</p>
                ) : (
                  <div className="space-y-2 text-sm text-gray-700">
                    {data.days.map((day) => {
                      const items = (data.schedule[day] || []);
                      return (
                        <p key={day}>
                          <span className="font-semibold">{day}:</span>{" "}
                          {items.length === 0 ? <span className="text-slate-400">No classes</span> :
                            items.map((s) => `${s.class} (${s.subject})`).join(", ")}
                        </p>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "schedule" && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm overflow-x-auto">
          {!data ? (
            <p className="text-slate-500">No timetable available yet.</p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-gray-900">📅 My Weekly Timetable</h3>
                <span className="text-xs text-slate-400">{data.timetable_name} · {data.timetable_status}</span>
              </div>
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr>
                    <th className="border bg-slate-100 px-2 py-2 text-left w-28">Period</th>
                    {data.days.map((d) => <th key={d} className="border bg-slate-100 px-2 py-2 text-left">{d}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {data.periods.map((p) => (
                    <tr key={p.number}>
                      <td className="border bg-slate-50 px-2 py-2 align-top">
                        <div className="font-medium text-slate-700">{p.is_zero ? "Zero" : `P${p.number}`}</div>
                        <div className="text-[11px] text-slate-400">{p.start}–{p.end}</div>
                      </td>
                      {data.days.map((day) => {
                        if (p.is_lunch) return <td key={day} className="border px-2 py-3 text-center text-amber-700 bg-amber-50 font-medium">Lunch</td>;
                        if (p.is_short_break) return <td key={day} className="border px-2 py-3 text-center text-green-700 bg-green-50 font-medium">Break</td>;
                        const c = cellByDayPeriod[`${day}|${p.number}`];
                        if (!c) return <td key={day} className="border px-2 py-3 text-center text-slate-300">—</td>;
                        return (
                          <td key={day} className="border px-2 py-2 bg-blue-50">
                            <div className="font-semibold text-slate-900">{c.class}</div>
                            <div className="text-xs text-slate-600">{c.subject}</div>
                            {c.room && <div className="text-[11px] text-slate-400">{c.room}</div>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      {activeTab === "attendance" && <AttendancePanel />}

      {activeTab === "exams" && <ExamsPanel />}

      {activeTab === "homework" && <AssignmentsPanel />}

      {activeTab === "announcements" && <AnnouncementsPanel />}

      {activeTab === "messages" && <MessagesPanel />}

      {activeTab === "calendar" && <CalendarPanel />}

      {activeTab === "library" && <LibraryPanel />}

      {activeTab === "myclass" && isClassTeacher && (
        <StudentManagement scopedGrade={user!.class_teacher_grade} scopedSection={user!.class_teacher_section} />
      )}

      {activeTab === "notifications" && <NotificationsCenter />}

      {showLeave && <LeaveModal onClose={() => setShowLeave(false)} onDone={(msg) => { setShowLeave(false); setNotice(msg); }} />}
    </div>
  );
}

function LeaveModal({ onClose, onDone }: { onClose: () => void; onDone: (msg: string) => void }) {
  const [date, setDate] = useState("");
  const [type, setType] = useState("casual");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!date) { setErr("Please choose a date."); return; }
    try {
      setSaving(true); setErr("");
      await api.leaves.request({ leave_date: date, reason, leave_type: type });
      onDone("Leave request submitted — your admin will review it.");
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't submit the leave request.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-slate-900 mb-4">📋 Request Leave</h3>
        {err && <div className="bg-red-100 border border-red-300 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}
        <label className="block text-sm font-medium text-slate-700 mb-1">Date</label>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="border rounded px-3 py-2 w-full mb-3" />
        <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
        <select value={type} onChange={(e) => setType(e.target.value)} className="border rounded px-3 py-2 w-full mb-3">
          <option value="casual">Casual</option>
          <option value="sick">Sick</option>
          <option value="personal">Personal</option>
          <option value="other">Other</option>
        </select>
        <label className="block text-sm font-medium text-slate-700 mb-1">Reason</label>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3}
          className="border rounded px-3 py-2 w-full mb-4" placeholder="Brief reason (optional)" />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700">Cancel</button>
          <button onClick={submit} disabled={saving}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-medium">
            {saving ? "Submitting…" : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
