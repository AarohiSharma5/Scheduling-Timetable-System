import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import { useOrgStore } from "./stores/orgStore";
import ProtectedRoute from "./components/ProtectedRoute";
import RequireOrg from "./components/RequireOrg";

// Pages
import LandingPage from "./pages/LandingPage";
import OrgLoginPage from "./pages/OrgLoginPage";
import OrgSignupPage from "./pages/OrgSignupPage";
import LoginPage from "./pages/LoginPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import AcceptInvitePage from "./pages/AcceptInvitePage";
import AdminPage from "./pages/AdminPage";
import PrincipalPage from "./pages/PrincipalPage";
import TeacherPage from "./pages/TeacherPage";
import StudentPage from "./pages/StudentPage";
import ParentPage from "./pages/ParentPage";

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
        <Route path="/org-signup" element={<OrgSignupPage />} />

        {/* Public token-link flows (no org/user session required) */}
        <Route path="/accept-invite/:token" element={<AcceptInvitePage />} />
        <Route path="/reset-password/:token" element={<ResetPasswordPage />} />

        {/* User login — only reachable after organization login */}
        <Route
          path="/login"
          element={
            <RequireOrg>
              <LoginPage />
            </RequireOrg>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <RequireOrg>
              <ForgotPasswordPage />
            </RequireOrg>
          }
        />

        {/* First-login forced password change (needs a user session) */}
        <Route
          path="/change-password"
          element={
            <ProtectedRoute>
              <ChangePasswordPage />
            </ProtectedRoute>
          }
        />

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
        <Route
          path="/parent"
          element={
            <ProtectedRoute requiredRole="parent">
              <ParentPage />
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
