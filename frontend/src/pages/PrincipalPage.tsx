import React from "react";
import { useAuthStore } from "../stores/authStore";
import PrincipalDashboardContent from "../components/PrincipalDashboardContent";

export default function PrincipalPage() {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-slate-900">📊 Principal Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">👤 {user?.name}</span>
            <button
              onClick={() => logout()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-md p-6">
          <PrincipalDashboardContent />
        </div>
      </main>
    </div>
  );
}
