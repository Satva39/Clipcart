import { Navigate, Outlet } from "react-router-dom";

function clearSupplierSession() {
  [
    "clipcart_supplier_access_token",
    "clipcart_supplier_refresh_token",
    "clipcart_supplier_user",
  ].forEach((key) => localStorage.removeItem(key));
}

export default function ProtectedSupplierRoute() {
  const token = localStorage.getItem("clipcart_supplier_access_token");
  const raw = localStorage.getItem("clipcart_supplier_user");
  let user = null;
  try {
    user = raw ? JSON.parse(raw) : null;
  } catch {
    /* invalid local session */
  }

  if (!token || !user) return <Navigate to="/login" replace />;
  if (String(user.role).toUpperCase() !== "SUPPLIER") {
    clearSupplierSession();
    return <Navigate to="/login" replace />;
  }
  if (String(user.status || "").toUpperCase() === "PENDING")
    return <Navigate to="/register/payment" replace />;
  if (user.status && String(user.status).toUpperCase() !== "ACTIVE")
    return <Navigate to="/account-status" replace />;
  return <Outlet />;
}
