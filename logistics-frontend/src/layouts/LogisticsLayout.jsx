import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  FaBars,
  FaBell,
  FaClipboardList,
  FaHistory,
  FaSignOutAlt,
  FaTachometerAlt,
  FaTimes,
  FaUserCircle,
} from "react-icons/fa";

import { REFRESH_KEY, USER_KEY, clearSession } from "../services/api";
import {
  getMe,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../services/logisticsService";
import "./LogisticsLayout.css";

function formatTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function LogisticsLayout() {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  });

  const unreadCount = notifications.filter((item) => !item.is_read).length;

  useEffect(() => {
    getMe()
      .then((data) => {
        setUser(data);
        localStorage.setItem(USER_KEY, JSON.stringify(data));
      })
      .catch(() => {
        // api interceptor handles expired/invalid sessions.
      });
  }, []);

  async function loadNotifications() {
    try {
      const data = await getNotifications();
      setNotifications(data);
    } catch {
      // Keep the current panel visible if a transient request fails.
    }
  }

  useEffect(() => {
    // Initial load is intentionally performed in the effect; the callback owns async state reconciliation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadNotifications();
    const interval = window.setInterval(loadNotifications, 15000);
    return () => window.clearInterval(interval);
  }, []);

  function logout() {
    clearSession();
    localStorage.removeItem(REFRESH_KEY);
    navigate("/login", { replace: true });
  }

  async function openNotifications() {
    await loadNotifications();
    setNotificationsOpen(true);
  }

  async function readNotification(id) {
    try {
      await markNotificationRead(id);
      setNotifications((current) =>
        current.map((item) =>
          item.id === id ? { ...item, is_read: true } : item,
        ),
      );
    } catch {
      // No-op; next poll will reconcile the state.
    }
  }

  async function readAll() {
    try {
      await markAllNotificationsRead();
      setNotifications((current) =>
        current.map((item) => ({ ...item, is_read: true })),
      );
    } catch {
      // No-op.
    }
  }

  const links = [
    { to: "/", label: "Dashboard", icon: <FaTachometerAlt />, end: true },
    {
      to: "/queue",
      label: "Delivery Queue",
      icon: <FaClipboardList />,
      end: true,
    },
    {
      to: "/queue/past-delivered-returned",
      label: "Past Delivered and Returned",
      icon: <FaHistory />,
      child: true,
    },
  ];

  return (
    <div className="logistics-shell">
      <aside className={`logistics-sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="logistics-sidebar-head">
          <div>
            <img
              className="logistics-logo-image"
              src="/clipcart-logo.png"
              alt="Clipcart"
              onError={(event) => {
                event.currentTarget.style.display = "none";
                event.currentTarget.nextElementSibling.style.display = "block";
              }}
            />
            <div className="logistics-logo logistics-logo-fallback">
              CLIPCART
            </div>
            <div className="logistics-logo-sub">LOGISTICS OPS</div>
          </div>
          <button
            type="button"
            className="logistics-mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <FaTimes />
          </button>
        </div>

        <nav className="logistics-nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `logistics-nav-link ${link.child ? "logistics-nav-link-child" : ""} ${isActive ? "active" : ""}`
              }
            >
              {link.icon}
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="logistics-sidebar-foot">
          <div className="logistics-user-mini">
            <FaUserCircle />
            <div>
              <strong>{user?.full_name || "Logistics manager"}</strong>
              <span>Authorized operations</span>
            </div>
          </div>
          <button type="button" className="logistics-logout" onClick={logout}>
            <FaSignOutAlt />
            Logout
          </button>
        </div>
      </aside>

      <div
        className={`logistics-mobile-backdrop ${mobileOpen ? "visible" : ""}`}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />

      <main className="logistics-main">
        <header className="logistics-topbar">
          <div className="logistics-topbar-left">
            <button
              type="button"
              className="logistics-menu-button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <FaBars />
            </button>
            <div>
              <div className="logistics-topbar-title">Delivery operations</div>
              <div className="logistics-topbar-subtitle">
                Monitor handoff, pickup and last-mile delivery.
              </div>
            </div>
          </div>

          <button
            type="button"
            className={`logistics-notification-button ${
              unreadCount ? "has-unread" : ""
            }`}
            onClick={openNotifications}
            aria-label="Open notifications"
          >
            <FaBell />
            {unreadCount > 0 && (
              <span>{unreadCount > 99 ? "99+" : unreadCount}</span>
            )}
          </button>
        </header>

        <div className="logistics-page">
          <Suspense
            fallback={
              <div className="logistics-loading" role="status" aria-busy="true">
                Loading operations…
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </div>
      </main>

      {notificationsOpen && (
        <div
          className="logistics-overlay"
          onClick={() => setNotificationsOpen(false)}
          role="presentation"
        >
          <aside
            className="logistics-notification-drawer"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="logistics-drawer-head">
              <div>
                <h2>Operational alerts</h2>
                <p>{unreadCount} unread</p>
              </div>
              <button
                type="button"
                onClick={() => setNotificationsOpen(false)}
                aria-label="Close notifications"
              >
                <FaTimes />
              </button>
            </div>

            {notifications.length === 0 ? (
              <div className="logistics-empty-mini">
                <FaBell />
                <strong>No alerts</strong>
                <span>Operational notifications will appear here.</span>
              </div>
            ) : (
              <div className="logistics-notification-list">
                {notifications.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`logistics-notification-item ${
                      item.is_read ? "read" : "unread"
                    }`}
                    onClick={() => readNotification(item.id)}
                  >
                    <div className="logistics-notification-dot" />
                    <div>
                      <strong>{item.title}</strong>
                      <span>{item.message}</span>
                      <small>{formatTime(item.created_at)}</small>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {notifications.length > 0 && (
              <button
                type="button"
                className="logistics-read-all"
                onClick={readAll}
              >
                Mark all as read
              </button>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
