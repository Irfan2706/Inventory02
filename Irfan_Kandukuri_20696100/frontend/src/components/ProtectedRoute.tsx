import { Navigate } from "react-router-dom";

import { useAuth } from "../state/AuthContext";
import type { Role } from "../types";

type ProtectedRouteProps = Readonly<{
  children: JSX.Element;
  allowedRoles?: Role[];
}>;

export function ProtectedRoute({
  children,
  allowedRoles,
}: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="p-8 text-sm text-slate-600">Loading session...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/products" replace />;
  }

  return children;
}
