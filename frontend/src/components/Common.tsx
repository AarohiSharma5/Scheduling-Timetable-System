import React from "react";

export const LoadingSpinner: React.FC = () => (
  <div className="flex items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600"></div>
  </div>
);

export const Alert: React.FC<{
  type: "error" | "success" | "info";
  message: string;
}> = ({ type, message }) => {
  const bgColor =
    type === "error"
      ? "bg-red-100"
      : type === "success"
        ? "bg-green-100"
        : "bg-blue-100";
  const textColor =
    type === "error"
      ? "text-red-800"
      : type === "success"
        ? "text-green-800"
        : "text-blue-800";

  return (
    <div className={`rounded-lg ${bgColor} p-4 ${textColor}`}>{message}</div>
  );
};

export const Header: React.FC = () => (
  <header className="border-b bg-white shadow-sm">
    <div className="mx-auto max-w-7xl px-6 py-4">
      <h1 className="text-2xl font-bold text-gray-900">Timetable Scheduler</h1>
      <p className="text-sm text-gray-600">Professional scheduling system</p>
    </div>
  </header>
);

export const Footer: React.FC = () => (
  <footer className="mt-12 border-t bg-gray-100 py-6">
    <div className="mx-auto max-w-7xl px-6 text-center text-sm text-gray-600">
      © 2024 Timetable Scheduler. All rights reserved.
    </div>
  </footer>
);
