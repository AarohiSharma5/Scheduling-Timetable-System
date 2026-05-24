import React from "react";
import { useAuthStore } from "../stores/authStore";

export default function StudentPage() {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Class Schedule</h1>
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
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-6xl mb-4">📚</div>
          <h2 className="text-2xl font-semibold mb-2">Your Class Timetable</h2>
          <p className="text-gray-600">Your weekly schedule will be displayed here.</p>
        </div>
      </main>
    </div>
  );
}
