import React, { useState, useEffect } from "react";
import { api } from "../api";
import LeaveManagement from "./LeaveManagement";
import NotificationsCenter from "./NotificationsCenter";
import TimetableGenerator from "./TimetableGenerator";

interface DashboardStats {
  total_students: number;
  total_teachers: number;
  total_batches: number;
  total_subjects: number;
  total_houses: number;
  leave_requests_pending: number;
}

export default function PrincipalDashboardContent() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "leaves" | "notifications" | "timetable">("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardStats();
  }, []);

  const loadDashboardStats = async () => {
    try {
      setLoading(true);
      // Get basic stats
      const teachersRes = await api.get("/admin/teachers");
      const leaveRes = await api.get("/leaves");
      
      setStats({
        total_students: 2800, // From seed data
        total_teachers: teachersRes.data?.length || 0,
        total_batches: 73, // From seed data
        total_subjects: 20, // From seed data
        total_houses: 4, // From seed data
        leave_requests_pending: leaveRes.data?.filter((l: any) => (l.status || "").toLowerCase() === "pending").length || 0,
      });
    } catch (error) {
      console.error("Error loading stats:", error);
    } finally {
      setLoading(false);
    }
  };

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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-orange-600">{stats.total_batches}</p>
                  <p className="text-sm text-gray-600">Classes/Sections</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-pink-600">{stats.total_subjects}</p>
                  <p className="text-sm text-gray-600">Subjects</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-indigo-600">{stats.total_houses}</p>
                  <p className="text-sm text-gray-600">House Groups</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-2xl font-bold text-cyan-600">34</p>
                  <p className="text-sm text-gray-600">Avg Students/Class</p>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-lg p-6 border-2 border-amber-200">
                <h3 className="font-bold text-amber-900 mb-4">📌 Quick Actions</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <button className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition">
                    📊 View Reports
                  </button>
                  <button className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition">
                    👥 Manage Staff
                  </button>
                  <button className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition">
                    📋 View Leaves
                  </button>
                  <button className="bg-white hover:bg-amber-50 text-amber-900 font-medium py-2 px-4 rounded-lg border border-amber-200 transition">
                    📚 Curriculum
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Leave Management Tab */}
      {activeTab === "leaves" && <LeaveManagement />}

      {/* Timetable Generator Tab */}
      {activeTab === "timetable" && <TimetableGenerator />}

      {/* Notifications Tab */}
      {activeTab === "notifications" && <NotificationsCenter />}
    </div>
  );
}
