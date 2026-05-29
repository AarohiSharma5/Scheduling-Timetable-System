import React, { useState, useEffect } from "react";
import { api } from "../api";
import NotificationsCenter from "./NotificationsCenter";

interface StudentInfo {
  name: string;
  class: string;
  section: string;
  rollNo: number;
  house: string;
}

export default function StudentDashboardContent() {
  const [studentInfo, setStudentInfo] = useState<StudentInfo | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "schedule" | "notifications">("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStudentInfo();
  }, []);

  const loadStudentInfo = async () => {
    try {
      setLoading(true);
      // Get student data from API
      const response = await api.get("/students?class=7&section=A");
      const firstStudent = response.data[0];

      if (firstStudent) {
        setStudentInfo({
          name: `${firstStudent.first_name} ${firstStudent.last_name}`,
          class: firstStudent.class_grade,
          section: firstStudent.section,
          rollNo: firstStudent.roll_no,
          house: firstStudent.house_name,
        });
      }
    } catch (error) {
      console.error("Error loading student info:", error);
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
          📊 My Info
        </button>
        <button
          onClick={() => setActiveTab("schedule")}
          className={`px-4 py-2 rounded-lg font-medium transition ${
            activeTab === "schedule"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          📅 My Timetable
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
            <p className="text-center py-8">⏳ Loading student info...</p>
          ) : studentInfo ? (
            <>
              {/* Student Info Card */}
              <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
                <h2 className="text-2xl font-bold text-blue-900 mb-4">👋 Welcome, {studentInfo.name}!</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-2xl font-bold text-blue-600">{studentInfo.class}</p>
                    <p className="text-sm text-gray-600">Class</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-2xl font-bold text-purple-600">{studentInfo.section}</p>
                    <p className="text-sm text-gray-600">Section</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-2xl font-bold text-green-600">{studentInfo.rollNo}</p>
                    <p className="text-sm text-gray-600">Roll Number</p>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <p className="text-2xl font-bold text-orange-600">{studentInfo.house}</p>
                    <p className="text-sm text-gray-600">House</p>
                  </div>
                </div>
              </div>

              {/* Student Statistics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
                  <p className="text-3xl font-bold text-purple-600">8</p>
                  <p className="text-gray-600 mt-2">Subjects</p>
                  <p className="text-xs text-gray-500 mt-1">This semester</p>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border-2 border-green-200">
                  <p className="text-3xl font-bold text-green-600">32 Hours</p>
                  <p className="text-gray-600 mt-2">Weekly Classes</p>
                  <p className="text-xs text-gray-500 mt-1">5 days/week</p>
                </div>

                <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-lg p-6 border-2 border-pink-200">
                  <p className="text-3xl font-bold text-pink-600">42</p>
                  <p className="text-gray-600 mt-2">Classmates</p>
                  <p className="text-xs text-gray-500 mt-1">In your section</p>
                </div>
              </div>

              {/* Quick Links */}
              <div className="bg-gradient-to-r from-cyan-50 to-cyan-100 rounded-lg p-6 border-2 border-cyan-200">
                <h3 className="font-bold text-cyan-900 mb-4">📌 Quick Links</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📚 My Classes
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    👨‍🏫 Teachers
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📖 Subjects
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📅 Events
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    📝 Assignments
                  </button>
                  <button className="bg-white hover:bg-cyan-50 text-cyan-900 font-medium py-2 px-4 rounded-lg border border-cyan-200 transition">
                    🏆 My Grades
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Schedule Tab */}
      {activeTab === "schedule" && (
        <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 className="font-bold text-gray-900 mb-4">📅 My Weekly Schedule</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="font-semibold text-gray-900 min-w-24">Monday</p>
              <p className="text-sm text-gray-600">English (7:45-8:45), Math (8:45-9:45), Science (10:00-11:00)</p>
            </div>
            <div className="flex items-center gap-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
              <p className="font-semibold text-gray-900 min-w-24">Tuesday</p>
              <p className="text-sm text-gray-600">Hindi (7:45-8:45), Social (8:45-9:45), PE (11:00-11:45)</p>
            </div>
            <div className="flex items-center gap-4 p-3 bg-green-50 rounded-lg border border-green-200">
              <p className="font-semibold text-gray-900 min-w-24">Wednesday</p>
              <p className="text-sm text-gray-600">Math (7:45-8:45), Science (8:45-9:45), Art (10:00-11:00)</p>
            </div>
            <div className="flex items-center gap-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="font-semibold text-gray-900 min-w-24">Thursday</p>
              <p className="text-sm text-gray-600">English (7:45-8:45), Computer (9:00-10:00), Music (11:00-11:45)</p>
            </div>
            <div className="flex items-center gap-4 p-3 bg-pink-50 rounded-lg border border-pink-200">
              <p className="font-semibold text-gray-900 min-w-24">Friday</p>
              <p className="text-sm text-gray-600">Science (7:45-8:45), Social (8:45-9:45), Assembly (9:45-10:30)</p>
            </div>
          </div>
          <button className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg">
            📥 Download Timetable PDF
          </button>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === "notifications" && <NotificationsCenter />}
    </div>
  );
}
