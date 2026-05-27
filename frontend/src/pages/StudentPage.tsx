import React from "react";
import StudentDashboardContent from "../components/StudentDashboardContent";

export default function StudentPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-7xl mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900">Student Dashboard</h1>
          <p className="text-gray-600 mt-2">View your classes, timetable, and notifications</p>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="p-6">
            <StudentDashboardContent />
          </div>
        </div>
      </div>
    </div>
  );
}
