import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  FaBars,
  FaBell,
  FaBoxOpen,
  FaChartLine,
  FaChartPie,
  FaChevronRight,
  FaSignOutAlt,
  FaTimes,
  FaUser,
  FaWallet,
  FaWarehouse,
  FaShoppingCart,
} from "react-icons/fa";
import { getUnreadNotificationCount } from "../services/notificationService";
import { getRegistrationStatus } from "../services/supplierService";
import SupplierStatusBanner from "../components/SupplierStatusBanner";
import { getSupplierProfile } from "../services/portalService";
import "./SupplierLayout.css";

const links = [
  ["/", "Dashboard", FaChartPie],
  ["/products", "Products", FaBoxOpen],
  ["/orders", "Orders", FaShoppingCart],
  ["/inventory", "Inventory", FaWarehouse],
  ["/analytics", "Analytics", FaChartLine],
  ["/earnings", "Earnings", FaWallet],
  ["/notifications", "Notifications", FaBell],
  ["/profile", "Profile & Settings", FaUser],
];

function clearSession() {
  [
    "clipcart_supplier_access_token",
    "clipcart_supplier_refresh_token",
    "clipcart_supplier_user",
    "clipcart_supplier_registration",
  ].forEach((key) => localStorage.removeItem(key));
}

export default function SupplierLayout() {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [profile, setProfile] = useState(null);
  const [statusChecked, setStatusChecked] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.allSettled([
      getRegistrationStatus(),
      getSupplierProfile(),
      getUnreadNotificationCount(),
    ]).then((results) => {
      if (!alive) return;
      const status =
        results[0].status === "fulfilled" ? results[0].value : null;
      const p = results[1].status === "fulfilled" ? results[1].value : null;
      const count = results[2].status === "fulfilled" ? results[2].value : 0;
      setProfile(p);
      setUnread(Number(count || 0));
      setStatusChecked(true);
      if (status && status.account_status !== "ACTIVE")
        navigate(
          status.registration_fee_paid
            ? "/account-status"
            : "/register/payment",
          { replace: true },
        );
    });
    const timer = window.setInterval(
      () =>
        getUnreadNotificationCount()
          .then((count) => alive && setUnread(Number(count || 0)))
          .catch(() => {}),
      30000,
    );
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [navigate]);

  function logout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  return (
    <div className="supplier-shell">
      <div
        className={`supplier-overlay ${mobileOpen ? "show" : ""}`}
        onClick={() => setMobileOpen(false)}
      />
      <aside className={`supplier-sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="supplier-logo-block">
          <div className="brand-mark">
            <img
              src="/clipcart-logo.png"
              alt="Clipcart"
              onError={(event) => {
                event.currentTarget.style.display = "none";
                event.currentTarget.nextElementSibling.style.display = "block";
              }}
            />
            <span className="brand-mark-fallback">CLIPCART</span>
            <span>SUPPLIER</span>
          </div>
          <button
            className="sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <FaTimes />
          </button>
        </div>
        <div className="supplier-account-mini">
          <div className="account-avatar">
            {(profile?.account?.full_name || "S").slice(0, 1).toUpperCase()}
          </div>
          <div>
            <strong>{profile?.account?.full_name || "Supplier"}</strong>
            <span>
              {profile?.business?.business_name || "Business account"}
            </span>
          </div>
        </div>
        <nav className="supplier-nav" aria-label="Supplier navigation">
          {links.map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `supplier-nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon />
              <span>{label}</span>
              {label === "Notifications" && unread > 0 ? (
                <b className="nav-badge">{unread > 99 ? "99+" : unread}</b>
              ) : (
                <FaChevronRight className="nav-arrow" />
              )}
            </NavLink>
          ))}
        </nav>
        <button className="supplier-logout" onClick={logout}>
          <FaSignOutAlt />
          <span>Logout</span>
        </button>
      </aside>
      <main className="supplier-main">
        <header className="supplier-topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <FaBars />
          </button>
          <div>
            <span className="topbar-kicker">Supplier workspace</span>
            <h1>Manage your Clipcart business</h1>
          </div>
          <button
            className="topbar-notify"
            onClick={() => navigate("/notifications")}
            aria-label="Open notifications"
          >
            <FaBell />
            {unread > 0 && <span>{unread > 9 ? "9+" : unread}</span>}
          </button>
        </header>
        {statusChecked && <SupplierStatusBanner profile={profile} />}
        <div className="supplier-content">
          <Suspense
            fallback={
              <div className="page-shell">
                <div className="notice">Loading workspace…</div>
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
