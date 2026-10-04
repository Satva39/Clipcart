import { useEffect, useState } from "react";
import { FaBell, FaCheckDouble, FaTrash } from "react-icons/fa";
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../services/notificationService";
import { formatDateTime } from "../../utils/dateRange";
import "../../styles/supplier-pages.css";

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    try {
      setItems(await getNotifications());
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load notifications.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function read(id) {
    try {
      await markNotificationRead(id);
      setItems((x) =>
        x.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to update notification.");
    }
  }
  async function readAll() {
    try {
      await markAllNotificationsRead();
      setItems((x) => x.map((n) => ({ ...n, is_read: true })));
    } catch (e) {
      setError(
        e?.response?.data?.message || "Unable to mark notifications read.",
      );
    }
  }
  async function remove(id) {
    try {
      await deleteNotification(id);
      setItems((x) => x.filter((n) => n.id !== id));
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to delete notification.");
    }
  }
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Notifications</h2>
          <p>
            New orders, fulfillment events, stock alerts and payout updates for
            this supplier account.
          </p>
        </div>
        {items.some((n) => !n.is_read) && (
          <button className="ghost-link" onClick={readAll}>
            <FaCheckDouble /> Mark all read
          </button>
        )}
      </div>
      {error && <div className="notice error">{error}</div>}
      {loading ? (
        <div className="panel empty-state">Loading notifications…</div>
      ) : items.length ? (
        <div className="notification-list">
          {items.map((n) => (
            <article
              className={`notification-card ${n.is_read ? "" : "unread"}`}
              key={n.id}
            >
              <div className="notification-large-icon">
                <FaBell />
              </div>
              <div className="notification-copy">
                <div className="notification-line">
                  <span className="status-chip neutral">{n.type}</span>
                  <time>{formatDateTime(n.created_at)}</time>
                </div>
                <h3>{n.title}</h3>
                <p>{n.message}</p>
                <div className="notification-actions">
                  {!n.is_read && (
                    <button className="ghost-link" onClick={() => read(n.id)}>
                      Mark read
                    </button>
                  )}
                  <button
                    className="icon-btn danger-btn"
                    onClick={() => remove(n.id)}
                    aria-label="Delete notification"
                  >
                    <FaTrash />
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="panel empty-state">
          <FaBell />
          <h3>No notifications</h3>
          <p>Supplier alerts and order events will appear here.</p>
        </div>
      )}
    </div>
  );
}
