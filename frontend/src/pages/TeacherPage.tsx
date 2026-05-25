import React, { useEffect, useState } from "react";
import { useAuthStore } from "../stores/authStore";
import { api } from "../api";
import { Plan } from "../types";
import TeacherDashboard from "../components/TeacherDashboard";
import { LoadingSpinner, Alert } from "../components/Common";
import { LogOut, Calendar } from "lucide-react";

export default function TeacherPage() {
  const { user, logout } = useAuthStore();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadTeacherPlan();
  }, [user?.id]);

  const loadTeacherPlan = async () => {
    try {
      setLoading(true);
      setError("");
      // Fetch the most recent published plan
      const plans = await api.plans.list();
      const publishedPlan = plans.find(
        (p) => p.status === "completed" || p.status === "draft"
      );

      if (publishedPlan) {
        setPlan(publishedPlan);
      } else {
        setError("No timetable plan found. Please contact administration.");
      }
    } catch (err) {
      setError("Failed to load your timetable. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Calendar className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  My Timetable
                </h1>
                <p className="text-sm text-gray-600">Weekly Class Schedule</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden md:block">
                <p className="text-sm text-gray-700 font-medium">{user?.name}</p>
                <p className="text-xs text-gray-500">Teacher</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 hover:text-red-700 rounded-lg transition-colors font-medium text-sm"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : error ? (
          <Alert type="error" message={error} />
        ) : plan ? (
          <>
            {/* Info Card */}
            <div className="mb-8 p-6 bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg">
              <h2 className="text-lg font-semibold text-blue-900 mb-2">
                {plan.title}
              </h2>
              <p className="text-sm text-blue-700">
                {plan.description || "Your weekly class schedule"}
              </p>
            </div>

            {/* Teacher Dashboard */}
            <TeacherDashboard
              plan={plan}
              teacherId={user?.id || 1}
              teacherName={user?.name || "Teacher"}
            />
          </>
        ) : (
          <Alert
            type="info"
            message="No timetable has been created yet. Please contact your administrator."
          />
        )}
      </main>
    </div>
  );
}
