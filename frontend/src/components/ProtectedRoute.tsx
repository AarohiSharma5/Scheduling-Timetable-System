import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { useOrgStore } from "../stores/orgStore";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string | string[];
}

export default function ProtectedRoute({
  children,
  requiredRole,
}: ProtectedRouteProps) {
  const { isAuthenticated, user, loading } = useAuthStore();
  const { organization } = useOrgStore();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mb-4"></div>
          <p className="text-slate-600">Loading…</p>
        </div>
      </div>
    );
  }

  // Step 1: an organization must be selected first.
  if (!organization) {
    return <Navigate to="/org-login" replace />;
  }

  // Step 2: user must then be authenticated.
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole) {
    const allowedRoles = Array.isArray(requiredRole)
      ? requiredRole
      : [requiredRole];

    if (!allowedRoles.includes(user.role)) {
      return <Navigate to="/login" replace />;
    }
  }

  return <>{children}</>;
}
