import { useEffect, useState } from "react";
import { FaBell, FaCheck, FaCheckDouble, FaTrash } from "react-icons/fa";
import {
  getAdminNotifications,
  markAdminNotificationRead,
  markAllAdminNotificationsRead,
  deleteAdminNotification,
} from "../services/notificationService";

export default function Notifications() {
  const [data, setData] = useState({ notifications: [], unread_count: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  async function load() {
    try {
      setLoading(true);
      const x = await getAdminNotifications();
      setData(x);
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load notifications.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);
  async function read(id) {
    try {
      await markAdminNotificationRead(id);
      setData((x) => ({
        ...x,
        unread_count: Math.max(0, x.unread_count - 1),
        notifications: x.notifications.map((n) =>
          n.id === id ? { ...n, is_read: true } : n,
        ),
      }));
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to update notification.",
      );
    }
  }
  async function remove(id) {
    if (!window.confirm("Delete this notification?")) return;
    setError("");
    setDeletingId(id);
    try {
      const target = data.notifications.find((n) => n.id === id);
      await deleteAdminNotification(id);
      setData((current) => ({
        ...current,
        unread_count: target?.is_read
          ? current.unread_count
          : Math.max(0, current.unread_count - 1),
        notifications: current.notifications.filter((n) => n.id !== id),
      }));
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to delete notification.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function readAll() {
    try {
      await markAllAdminNotificationsRead();
      setData((x) => ({
        ...x,
        unread_count: 0,
        notifications: x.notifications.map((n) => ({ ...n, is_read: true })),
      }));
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to update notifications.",
      );
    }
  }
  return (
    <div className="admin-page">
      <div className="admin-page-header admin-page-header-row">
        <div>
          <span className="admin-eyebrow">SYSTEM NOTIFICATIONS</span>
          <h1>Notifications</h1>
          <p>
            Supplier registration, platform payments, delivery and other
            operational alerts.
          </p>
        </div>
        {data.unread_count > 0 && (
          <button className="admin-primary-btn" onClick={readAll}>
            <FaCheckDouble /> Mark all read
          </button>
        )}
      </div>
      {error && <div className="admin-error">{error}</div>}
      {loading ? (
        <div className="admin-empty">Loading notifications…</div>
      ) : !data.notifications.length ? (
        <div className="admin-table-card">
          <div className="admin-empty">
            <FaBell /> No notifications.
          </div>
        </div>
      ) : (
        <div className="admin-notification-list">
          {data.notifications.map((n) => (
            <div
              className={`admin-notification-card ${n.is_read ? "read" : "unread"}`}
              key={n.id}
            >
              <div className="admin-notification-icon">
                <FaBell />
              </div>
              <div className="admin-notification-content">
                <div className="admin-notification-top">
                  <div>
                    <h3>{n.title}</h3>
                    <span>{n.type}</span>
                  </div>
                  <small>
                    {n.created_at
                      ? new Date(n.created_at).toLocaleString("en-IN")
                      : "—"}
                  </small>
                </div>
                <p>{n.message}</p>
                <div className="admin-notification-actions">
                  {!n.is_read && (
                    <button
                      className="admin-notification-read-btn"
                      onClick={() => read(n.id)}
                    >
                      <FaCheck /> Mark as read
                    </button>
                  )}
                  <button
                    type="button"
                    className="admin-notification-delete-btn"
                    onClick={() => remove(n.id)}
                    disabled={deletingId === n.id}
                    aria-label={`Delete notification: ${n.title}`}
                  >
                    <FaTrash /> {deletingId === n.id ? "Deleting…" : "Delete"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
