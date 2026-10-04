import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import adminApi, { clearAdminSession } from "../services/api";

export default function ProtectedAdminRoute() {
  const [state, setState] = useState(() =>
    sessionStorage.getItem("clipcart_admin_access_token")
      ? "checking"
      : "unauthorized",
  );

  useEffect(() => {
    let active = true;
    sessionStorage.removeItem("clipcart_admin_email");

    const token = sessionStorage.getItem("clipcart_admin_access_token");
    if (!token) return;

    adminApi
      .get("/admin/profile")
      .then((response) => {
        const role = String(response.data?.data?.role || "").toUpperCase();
        if (role !== "ADMIN") throw new Error("Not an admin account.");
        if (active) setState("authorized");
      })
      .catch(() => {
        clearAdminSession();
        if (active) setState("unauthorized");
      });

    return () => {
      active = false;
    };
  }, []);

  if (state === "checking") {
    return (
      <div className="admin-auth-page">
        <div className="admin-auth-card">Checking secure admin session…</div>
      </div>
    );
  }
  return state === "authorized" ? <Outlet /> : <Navigate to="/login" replace />;
}
