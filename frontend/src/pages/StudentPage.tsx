import React, { useEffect, useState } from "react";
import { useAuthStore } from "../stores/authStore";
import StudentDashboard from "../components/StudentDashboard";
import type { Plan } from "../types";
import { api } from "../api";

export default function StudentPage() {
  const { user } = useAuthStore();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStudentPlan();
  }, [user?.id]);

  const loadStudentPlan = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch published plans
      const plans = await api.plans.list();

      if (plans.length === 0) {
        setError("No timetable available yet. Please check back later.");
        return;
      }

      // Get the first published/completed plan
      const publishedPlan = plans.find(
        (p: any) => p.status === "completed" || p.status === "published"
      ) || plans[0];

      setPlan(publishedPlan);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load timetable"
      );
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 mb-4 rounded-full bg-blue-100 animate-spin">
            <div className="w-8 h-8 bg-blue-500 rounded-full"></div>
          </div>
          <p className="text-slate-600">Loading your timetable...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Error</h2>
          <p className="text-slate-600 mb-6">{error}</p>
          <button
            onClick={loadStudentPlan}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-4xl mb-4">📅</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">
            No Timetable Available
          </h2>
          <p className="text-slate-600">
            The school timetable will be available soon. Please check back later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <StudentDashboard
      plan={plan}
      studentId={user?.id || 0}
      studentName={user?.name || "Student"}
      batchName={
        plan.school_profile?.institution_name || "Your Class"
      }
    />
  );
}
