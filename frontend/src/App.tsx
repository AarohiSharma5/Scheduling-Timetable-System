import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import ProtectedRoute from "./components/ProtectedRoute";

// Pages
import LoginPage from "./pages/LoginPage";
import AdminPage from "./pages/AdminPage";
import PrincipalPage from "./pages/PrincipalPage";
import TeacherPage from "./pages/TeacherPage";
import StudentPage from "./pages/StudentPage";

const App: React.FC = () => {
  const { restoreSession, error } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (error) {
      console.error("Auth error:", error);
    }
  }, [error]);

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <AdminPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/principal"
          element={
            <ProtectedRoute requiredRole="principal">
              <PrincipalPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/teacher"
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/student"
          element={
            <ProtectedRoute requiredRole="student">
              <StudentPage />
            </ProtectedRoute>
          }
        />

        {/* Default redirect to login */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
