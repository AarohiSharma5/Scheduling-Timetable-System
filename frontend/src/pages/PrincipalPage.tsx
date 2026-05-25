import React, { useEffect, useState } from "react";
import { useAuthStore } from "../stores/authStore";
import PrincipalDashboard from "../components/PrincipalDashboard";
import type { TimetableAnalytics } from "../types";
import { api } from "../api";

export default function PrincipalPage() {
  const { user } = useAuthStore();
  const [analytics, setAnalytics] = useState<TimetableAnalytics | null>(null);
  const [planId, setPlanId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get the latest published plan
      const plans = await api.plans.list();
      if (plans.length === 0) {
        setError("No timetable available. Please create and publish a timetable first.");
        return;
      }

      const publishedPlan =
        plans.find((p: any) => p.status === "completed" || p.status === "published") ||
        plans[0];

      setPlanId(publishedPlan.id);

      // Fetch analytics for this plan
      const analyticsData = await api.analytics.get(publishedPlan.id);
      setAnalytics(analyticsData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load analytics"
      );
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 mb-4 rounded-full bg-indigo-100 animate-spin">
            <div className="w-8 h-8 bg-indigo-500 rounded-full"></div>
          </div>
          <p className="text-slate-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Error</h2>
          <p className="text-slate-600 mb-6">{error}</p>
          <button
            onClick={loadAnalytics}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-4xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">
            No Analytics Available
          </h2>
          <p className="text-slate-600">
            Analytics data could not be loaded. Please check back later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <PrincipalDashboard
      analytics={analytics}
      onRefresh={loadAnalytics}
    />
  );
}
