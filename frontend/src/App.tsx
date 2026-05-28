import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import { useOrgStore } from "./stores/orgStore";
import ProtectedRoute from "./components/ProtectedRoute";

// Pages
import LandingPage from "./pages/LandingPage";
import OrgLoginPage from "./pages/OrgLoginPage";
import LoginPage from "./pages/LoginPage";
import AdminPage from "./pages/AdminPage";
import PrincipalPage from "./pages/PrincipalPage";
import TeacherPage from "./pages/TeacherPage";
import StudentPage from "./pages/StudentPage";

const App: React.FC = () => {
  const { restoreSession, error } = useAuthStore();
  const { restoreOrgSession } = useOrgStore();

  useEffect(() => {
    restoreOrgSession();
    restoreSession();
  }, [restoreOrgSession, restoreSession]);

  useEffect(() => {
    if (error) {
      console.error("Auth error:", error);
    }
  }, [error]);

  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/org-login" element={<OrgLoginPage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Routes (require org session + user auth) */}
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

        {/* Fallback to landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
