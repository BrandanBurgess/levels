import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { LandingPage } from "../features/landing/LandingPage";
import { useAuth } from "./context";

export function MemberAccess() {
  const { isAuthenticated, isRestoring } = useAuth();
  const location = useLocation();

  if (isRestoring) {
    return (
      <main className="auth-route-status" aria-live="polite">
        <p role="status">Restoring your account…</p>
      </main>
    );
  }
  if (isAuthenticated) return <Outlet />;
  if (location.pathname === "/") return <LandingPage />;
  return <Navigate replace state={{ from: `${location.pathname}${location.search}` }} to="/login" />;
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const { isAuthenticated, isRestoring } = useAuth();
  if (isRestoring) return null;
  return isAuthenticated ? <Navigate replace to="/" /> : children;
}
