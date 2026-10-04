import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function ProtectedRoute() {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="cc-page-shell">
        <div className="cc-container">
          <div
            className="cc-skeleton cc-skeleton-panel"
            aria-label="Loading account"
          />
        </div>
      </div>
    );
  }

  if (!isAuthenticated || user?.role !== "CUSTOMER") {
    const redirect = `${location.pathname}${location.search}${location.hash}`;
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(redirect)}`}
        replace
      />
    );
  }

  return <Outlet />;
}
