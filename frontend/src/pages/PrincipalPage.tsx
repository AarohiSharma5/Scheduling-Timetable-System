import React from "react";
import { useAuthStore } from "../stores/authStore";

export default function PrincipalPage() {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Principal Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.name}</span>
            <button
              onClick={() => logout()}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            { title: "Teacher Workload", icon: "📊" },
            { title: "Batch Overview", icon: "📚" },
            { title: "Timetable Status", icon: "📅" },
          ].map((item) => (
            <div key={item.title} className="bg-white rounded-lg shadow p-6">
              <div className="text-3xl mb-2">{item.icon}</div>
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="text-gray-500 text-sm">Coming soon...</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
