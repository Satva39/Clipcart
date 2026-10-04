import { Suspense } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { logoutAdmin } from "../services/authService";

const links = [
  ["/", "Dashboard"],
  ["/customers", "Customers"],
  ["/suppliers", "Suppliers"],
  ["/logistics", "Logistics"],
  ["/orders", "Orders"],
  ["/products", "Platform Products"],
  ["/banners", "Banners"],
  ["/settings", "Settings"],
  ["/payouts", "Payouts"],
  ["/analytics", "Analytics"],
  ["/notifications", "Notifications"],
  ["/audit-logs", "Audit Log"],
  ["/profile", "Profile"],
];

export default function AdminLayout() {
  const location = useLocation();

  async function logout() {
    await logoutAdmin();
    window.location.href = "/login";
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <img
            className="admin-brand-image"
            src="/clipcart-logo.png"
            alt="Clipcart"
            onError={(event) => {
              event.currentTarget.style.display = "none";
              event.currentTarget.nextElementSibling.style.display = "block";
            }}
          />
          <div className="admin-brand-logo admin-brand-fallback">Clipcart</div>
          <div className="admin-brand-label">PRIVATE ADMIN</div>
        </div>
        <nav className="admin-nav" aria-label="Admin navigation">
          {links.map(([path, label]) => {
            const active =
              path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(path);
            return (
              <Link key={path} to={path} className={active ? "active" : ""}>
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="admin-sidebar-footer">
          <button type="button" onClick={logout} className="admin-logout-btn">
            Logout
          </button>
        </div>
      </aside>
      <main className="admin-content">
        <Suspense
          fallback={
            <div className="admin-page">
              <div className="admin-empty">Loading admin workspace…</div>
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}
