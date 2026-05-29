import React from "react";
import { Navigate } from "react-router-dom";
import { useOrgStore } from "../stores/orgStore";

interface RequireOrgProps {
  children: React.ReactNode;
}

/**
 * Route guard that blocks access until an organization session exists.
 * Used to gate the user-login step (/login) behind organization login.
 */
export default function RequireOrg({ children }: RequireOrgProps) {
  const { organization } = useOrgStore();

  if (!organization) {
    return <Navigate to="/org-login" replace />;
  }

  return <>{children}</>;
}
