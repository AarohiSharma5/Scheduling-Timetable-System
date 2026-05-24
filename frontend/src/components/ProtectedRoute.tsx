import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string | string[];
}

export default function ProtectedRoute({
  children,
  requiredRole,
}: ProtectedRouteProps) {
  const { isAuthenticated, user, loading } = useAuthStore();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white mb-4"></div>
          <p className="text-white">Loading...</p>
        </div>
      </div>
    );
  }

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
