import { Navigate, Outlet } from "react-router-dom";
import { ACCESS_KEY, USER_KEY } from "../services/api";

export default function ProtectedLogisticsRoute() {
  const token = localStorage.getItem(ACCESS_KEY);
  const user = (() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  })();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  const isLogistics =
    String(user.role || "").toUpperCase() === "LOGISTICS_MANAGER" &&
    String(user.status || "").toUpperCase() === "ACTIVE";

  if (!isLogistics) {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(USER_KEY);
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
