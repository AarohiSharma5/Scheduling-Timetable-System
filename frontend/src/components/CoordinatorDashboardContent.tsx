import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import AttendancePanel from "./AttendancePanel";
import ExamsPanel from "./ExamsPanel";
import AssignmentsPanel from "./AssignmentsPanel";
import AnnouncementsPanel from "./AnnouncementsPanel";
import AnalyticsPanel from "./AnalyticsPanel";
import CalendarPanel from "./CalendarPanel";
import MessagesPanel from "./MessagesPanel";

interface DashboardStats {
  total_students: number;
  total_teachers: number;
  total_batches: number;
  total_subjects: number;
}

interface TodayAttendance {
  present_percentage: number | null;
  classes_marked: number;
  total_classes: number;
  total_marked: number;
}

type Tab =
  | "overview"
  | "timetable"
  | "attendance"
  | "exams"
  | "homework"
  | "announcements"
  | "analytics"
  | "calendar"
  | "messages";

const TABS: [Tab, string][] = [
  ["overview", "📊 Overview"],
  ["timetable", "📅 Timetables"],
  ["attendance", "📝 Attendance"],
  ["exams", "🧪 Exams"],
  ["homework", "📒 Homework"],
  ["announcements", "📣 Announcements"],
  ["analytics", "📈 Analytics"],
  ["calendar", "🗓️ Calendar"],
  ["messages", "💬 Messages"],
];

export default function CoordinatorDashboardContent() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [todayAtt, setTodayAtt] = useState<TodayAttendance | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [dbStats, todayRes] = await Promise.all([
          api.stats(),
          api.attendance.today().catch(() => null),
        ]);
        setStats({
          total_students: dbStats?.students || 0,
          total_teachers: dbStats?.teachers || 0,
          total_batches: dbStats?.batches || 0,
          total_subjects: dbStats?.subjects || 0,
        });
        if (todayRes) setTodayAtt(todayRes);
      } catch (e) {
        console.error("Error loading coordinator stats:", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex gap-2 flex-wrap">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === key
                ? "bg-indigo-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          {loading ? (
            <p className="text-center py-8">⏳ Loading dashboard…</p>
          ) : stats ? (
            <>
              <div className="bg-gradient-to-r from-indigo-50 to-indigo-100 rounded-lg p-6 border-2 border-indigo-200">
                <h2 className="text-xl font-bold text-indigo-900 mb-1">
                  🧭 Academic Coordination
                </h2>
                <p className="text-sm text-indigo-800/80">
                  Oversee attendance, exams, homework and communication across the school.
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
                  <p className="text-3xl font-bold text-blue-600">{stats.total_students}</p>
                  <p className="text-gray-600 mt-2">Students</p>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
                  <p className="text-3xl font-bold text-purple-600">{stats.total_teachers}</p>
                  <p className="text-gray-600 mt-2">Teachers</p>
                </div>
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-6 border-2 border-orange-200">
                  <p className="text-3xl font-bold text-orange-600">{stats.total_batches}</p>
                  <p className="text-gray-600 mt-2">Classes/Sections</p>
                </div>
                <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-lg p-6 border-2 border-pink-200">
                  <p className="text-3xl font-bold text-pink-600">{stats.total_subjects}</p>
                  <p className="text-gray-600 mt-2">Subjects</p>
                </div>
              </div>

              <div className="bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-lg p-6 border-2 border-emerald-200">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-bold text-emerald-900">📝 Today's Attendance</h3>
                  <button
                    onClick={() => setActiveTab("attendance")}
                    className="text-sm text-emerald-800 underline"
                  >
                    Open
                  </button>
                </div>
                {todayAtt && todayAtt.total_marked > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-2">
                    <div>
                      <p className="text-3xl font-bold text-emerald-700">
                        {todayAtt.present_percentage ?? "—"}%
                      </p>
                      <p className="text-sm text-gray-600">Present today</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-emerald-700">
                        {todayAtt.classes_marked}/{todayAtt.total_classes}
                      </p>
                      <p className="text-sm text-gray-600">Classes marked</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-emerald-700">{todayAtt.total_marked}</p>
                      <p className="text-sm text-gray-600">Students recorded</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-emerald-800 mt-1">
                    No attendance recorded yet today.
                  </p>
                )}
              </div>

              <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-lg p-6 border-2 border-amber-200">
                <h3 className="font-bold text-amber-900 mb-4">📌 Quick Actions</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {([
                    ["timetable", "📅 View Timetables"],
                    ["attendance", "📝 Attendance"],
                    ["exams", "🧪 Exams"],
                    ["announcements", "📣 Announce"],
                  ] as [Tab, string][]).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setActiveTab(key)}
                      className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {activeTab === "timetable" && <CoordinatorTimetableView />}
      {activeTab === "attendance" && <AttendancePanel />}
      {activeTab === "exams" && <ExamsPanel />}
      {activeTab === "homework" && <AssignmentsPanel />}
      {activeTab === "announcements" && <AnnouncementsPanel />}
      {activeTab === "analytics" && <AnalyticsPanel />}
      {activeTab === "calendar" && <CalendarPanel />}
      {activeTab === "messages" && <MessagesPanel />}
    </div>
  );
}

/* ---------- Read-only timetable viewer (pick a class, view its week) ---------- */

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
  teacher: string | null;
  room: string | null;
  is_lunch: boolean;
  is_short_break: boolean;
}
interface BatchSchedule {
  batch: { grade: string; section: string };
  schedule: Record<string, SlotCell[]>;
  periods: PeriodRow[];
  days: string[];
  timetable_name: string;
  timetable_status: string;
}
interface BatchOption {
  id: number;
  grade?: string;
  section?: string;
  name?: string;
}

function CoordinatorTimetableView() {
  const [batches, setBatches] = useState<BatchOption[]>([]);
  const [batchId, setBatchId] = useState<number | "">("");
  const [data, setData] = useState<BatchSchedule | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.admin.batches
      .list()
      .then((list: BatchOption[]) => {
        setBatches(list || []);
        if (list && list.length > 0) setBatchId(list[0].id);
      })
      .catch(() => setError("Couldn't load classes."));
  }, []);

  useEffect(() => {
    if (batchId === "") return;
    const load = async () => {
      try {
        setLoading(true);
        setError("");
        const res = await api.timetable.getBatchSchedule(Number(batchId));
        setData(res);
      } catch (e: any) {
        setData(null);
        setError(
          e?.response?.data?.error ||
            "No timetable available for this class yet."
        );
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [batchId]);

  const cellByDayPeriod = useMemo(() => {
    const m: Record<string, SlotCell> = {};
    if (data) {
      for (const day of Object.keys(data.schedule)) {
        for (const c of data.schedule[day]) m[`${day}|${c.period}`] = c;
      }
    }
    return m;
  }, [data]);

  const labelFor = (b: BatchOption) =>
    b.name || `${b.grade ?? ""}-${b.section ?? ""}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm font-medium text-slate-700">Class:</label>
        <select
          value={batchId}
          onChange={(e) => setBatchId(e.target.value ? Number(e.target.value) : "")}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm"
        >
          {batches.map((b) => (
            <option key={b.id} value={b.id}>
              {labelFor(b)}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="text-center py-8 text-slate-500">⏳ Loading timetable…</p>}

      {!loading && error && (
        <div className="bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm overflow-x-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-gray-900">
              📅 {data.batch.grade}-{data.batch.section} Weekly Timetable
            </h3>
            <span className="text-xs text-slate-400">
              {data.timetable_name} · {data.timetable_status}
            </span>
          </div>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border bg-slate-100 px-2 py-2 text-left w-28">Period</th>
                {data.days.map((d) => (
                  <th key={d} className="border bg-slate-100 px-2 py-2 text-left">
                    {d}
                  </th>
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
                    <div className="text-[11px] text-slate-400">
                      {p.start}–{p.end}
                    </div>
                  </td>
                  {data.days.map((day) => {
                    const c = cellByDayPeriod[`${day}|${p.number}`];
                    if (p.is_lunch || c?.is_lunch) {
                      return (
                        <td
                          key={day}
                          className="border px-2 py-3 text-center text-amber-700 bg-amber-50 font-medium"
                        >
                          Lunch
                        </td>
                      );
                    }
                    if (p.is_short_break || c?.is_short_break) {
                      return (
                        <td
                          key={day}
                          className="border px-2 py-3 text-center text-green-700 bg-green-50 font-medium"
                        >
                          Break
                        </td>
                      );
                    }
                    if (!c) {
                      return (
                        <td key={day} className="border px-2 py-3 text-center text-slate-300">
                          —
                        </td>
                      );
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
    </div>
  );
}
