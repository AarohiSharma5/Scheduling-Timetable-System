import React, { useState, useEffect } from "react";
import { api } from "../api";
import LeaveManagement from "./LeaveManagement";
import NotificationsCenter from "./NotificationsCenter";
import TimetableGenerator from "./TimetableGenerator";
import AttendancePanel from "./AttendancePanel";
import ExamsPanel from "./ExamsPanel";
import AnnouncementsPanel from "./AnnouncementsPanel";

interface DashboardStats {
  total_students: number;
  total_teachers: number;
  total_batches: number;
  total_subjects: number;
  leave_requests_pending: number;
}

interface TodayAttendance {
  present_percentage: number | null;
  classes_marked: number;
  total_classes: number;
  total_marked: number;
}

export default function PrincipalDashboardContent() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [todayAtt, setTodayAtt] = useState<TodayAttendance | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "attendance" | "exams" | "announcements" | "leaves" | "notifications" | "timetable">("overview");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    loadDashboardStats();
  }, []);

  const loadDashboardStats = async () => {
    try {
      setLoading(true);
      // Real, organization-scoped counts from the backend (never hardcoded).
      const [dbStats, leaveRes, todayRes] = await Promise.all([
        api.stats(),
        api.get("/leaves"),
        api.attendance.today().catch(() => null),
      ]);

      setStats({
        total_students: dbStats?.students || 0,
        total_teachers: dbStats?.teachers || 0,
        total_batches: dbStats?.batches || 0,
        total_subjects: dbStats?.subjects || 0,
        leave_requests_pending:
          leaveRes.data?.filter((l: any) => (l.status || "").toLowerCase() === "pending").length || 0,
      });
      if (todayRes) setTodayAtt(todayRes);
    } catch (error) {
      console.error("Error loading stats:", error);
    } finally {
      setLoading(false);
    }
  };

  // Derived, not hardcoded: average section strength.
  const avgStudentsPerClass = (s: DashboardStats) =>
    s.total_batches > 0 ? Math.round(s.total_students / s.total_batches) : 0;

  return (
    <div className="space-y-6">
      {/* Header Navigation */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "overview"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📊 Overview
        </button>
        <button
          onClick={() => setActiveTab("leaves")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "leaves"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📋 Leave Requests
        </button>
        <button
          onClick={() => setActiveTab("attendance")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "attendance"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📝 Attendance
        </button>
        <button
          onClick={() => setActiveTab("exams")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "exams"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          🧪 Exams
        </button>
        <button
          onClick={() => setActiveTab("announcements")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "announcements"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📣 Announcements
        </button>
        <button
          onClick={() => setActiveTab("timetable")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "timetable"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📊 Timetable
        </button>
        <button
          onClick={() => setActiveTab("notifications")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "notifications"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          🔔 Notifications
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {loading ? (
            <p className="text-center py-8">⏳ Loading dashboard...</p>
          ) : stats ? (
            <>
              {/* Statistics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
                  <p className="text-3xl font-bold text-blue-600">{stats.total_students}</p>
                  <p className="text-gray-600 mt-2">Total Students</p>
                  <p className="text-xs text-gray-500 mt-1">All classes (Nursery to Class 12)</p>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
                  <p className="text-3xl font-bold text-purple-600">{stats.total_teachers}</p>
                  <p className="text-gray-600 mt-2">Total Teachers</p>
                  <p className="text-xs text-gray-500 mt-1">NTT, PRT, TGT, PGT, Specialists</p>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border-2 border-green-200">
                  <p className="text-3xl font-bold text-green-600">{stats.leave_requests_pending}</p>
                  <p className="text-gray-600 mt-2">Pending Leave Requests</p>
                  <p className="text-xs text-gray-500 mt-1">Awaiting your approval</p>
                </div>
              </div>

              {/* Additional Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-orange-600">{stats.total_batches}</p>
                  <p className="text-sm text-gray-600">Classes/Sections</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-pink-600">{stats.total_subjects}</p>
                  <p className="text-sm text-gray-600">Subjects</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-cyan-600">{avgStudentsPerClass(stats)}</p>
                  <p className="text-sm text-gray-600">Avg Students/Class</p>
                </div>
              </div>

              {/* Today's attendance snapshot */}
              <div className="bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-lg p-6 border-2 border-emerald-200">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-bold text-emerald-900">📝 Today's Attendance</h3>
                  <button onClick={() => setActiveTab("attendance")}
                          className="text-sm text-emerald-800 underline">Open</button>
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
                  <p className="text-sm text-emerald-800 mt-1">No attendance recorded yet today.</p>
                )}
              </div>

              {/* Quick Actions */}
              <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-lg p-6 border-2 border-amber-200">
                <h3 className="font-bold text-amber-900 mb-4">📌 Quick Actions</h3>
                {notice && (
                  <div className="mb-3 bg-white border border-amber-300 text-amber-900 text-sm rounded-lg px-3 py-2">
                    {notice}
                  </div>
                )}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <button
                    onClick={() => setActiveTab("timetable")}
                    className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition"
                  >
                    📊 View Timetable
                  </button>
                  <button
                    onClick={() => setActiveTab("leaves")}
                    className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition"
                  >
                    📋 Leave Requests
                  </button>
                  <button
                    onClick={() => setActiveTab("notifications")}
                    className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition"
                  >
                    🔔 Notifications
                  </button>
                  <button
                    onClick={() => setNotice(
                      `Staff & curriculum management is handled in the Admin dashboard. This school has ${stats.total_teachers} teachers and ${stats.total_subjects} subjects.`
                    )}
                    className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition"
                  >
                    👥 Staff & Curriculum
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Attendance Tab */}
      {activeTab === "attendance" && <AttendancePanel />}

      {activeTab === "exams" && <ExamsPanel />}

      {activeTab === "announcements" && <AnnouncementsPanel />}

      {/* Leave Management Tab */}
      {activeTab === "leaves" && <LeaveManagement />}

      {/* Timetable Generator Tab */}
      {activeTab === "timetable" && <TimetableGenerator />}

      {/* Notifications Tab */}
      {activeTab === "notifications" && <NotificationsCenter />}
    </div>
  );
}
