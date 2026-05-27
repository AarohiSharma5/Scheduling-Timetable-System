import React, { useState, useEffect } from "react";
import { api } from "../api";
import NotificationsCenter from "./NotificationsCenter";

interface TeacherStats {
  classes: number;
  students: number;
  subjects: number;
}

export default function TeacherDashboardContent() {
  const [stats, setStats] = useState<TeacherStats>({ classes: 0, students: 0, subjects: 0 });
  const [activeTab, setActiveTab] = useState<"overview" | "schedule" | "notifications">("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTeacherStats();
  }, []);

  const loadTeacherStats = async () => {
    try {
      setLoading(true);
      // Get teacher data
      const response = await api.get("/api/teachers");
      const teachers = response.data;
      const firstTeacher = teachers[0];

      // Extract stats from first teacher
      setStats({
        classes: firstTeacher.assigned_batches?.length || 0,
        students: 30, // Average
        subjects: firstTeacher.subject_ids?.length || 1,
      });
    } catch (error) {
      console.error("Error loading teacher stats:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "overview"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📊 My Schedule
        </button>
        <button
          onClick={() => setActiveTab("schedule")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "schedule"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📅 Timetable
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
          ) : (
            <>
              {/* Statistics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
                  <p className="text-3xl font-bold text-blue-600">{stats.classes}</p>
                  <p className="text-gray-600 mt-2">Classes Assigned</p>
                  <p className="text-xs text-gray-500 mt-1">Different grades/sections</p>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
                  <p className="text-3xl font-bold text-purple-600">{stats.students}</p>
                  <p className="text-gray-600 mt-2">Total Students</p>
                  <p className="text-xs text-gray-500 mt-1">Across all assigned classes</p>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border-2 border-green-200">
                  <p className="text-3xl font-bold text-green-600">{stats.subjects}</p>
                  <p className="text-gray-600 mt-2">Subject(s) Taught</p>
                  <p className="text-xs text-gray-500 mt-1">Primary teaching assignments</p>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-gradient-to-r from-cyan-50 to-cyan-100 rounded-lg p-6 border-2 border-cyan-200">
                <h3 className="font-bold text-cyan-900 mb-4">📌 Quick Actions</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📊 My Timetable
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📚 My Classes
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📋 Request Leave
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📝 Mark Attendance
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📞 Contact Principal
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    🎓 View Profile
                  </button>
                </div>
              </div>

              {/* This Week's Schedule */}
              <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
                <h3 className="font-bold text-gray-900 mb-4">📅 This Week's Schedule</h3>
                <div className="space-y-2 text-sm text-gray-600">
                  <p>Monday: Class 7A (English), Class 8B (English)</p>
                  <p>Tuesday: Class 7A (English), Class 9C (English)</p>
                  <p>Wednesday: Class 7A (English), Class 10A (English)</p>
                  <p>Thursday: Class 7A (English), Class 8B (English)</p>
                  <p>Friday: Class 7A (English), Class 9C (English)</p>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Schedule Tab */}
      {activeTab === "schedule" && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 className="font-bold text-gray-900 mb-4">📊 Complete Timetable</h3>
          <p className="text-gray-600 mb-4">Your PDF timetable will be available here soon. You can download it from the Portal or ask your Principal.</p>
          <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg">
            📥 Download My Timetable PDF
          </button>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === "notifications" && <NotificationsCenter />}
    </div>
  );
}
