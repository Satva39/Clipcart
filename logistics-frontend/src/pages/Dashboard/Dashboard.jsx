import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FaRedoAlt,
  FaBell,
  FaBoxOpen,
  FaCheckCircle,
  FaClipboardList,
  FaClock,
  FaExclamationTriangle,
  FaRoute,
  FaShippingFast,
  FaTruckLoading,
} from "react-icons/fa";

import { getDashboard } from "../../services/logisticsService";
import "./dashboard.css";

const metricCards = [
  ["new_orders_awaiting_processing", "Awaiting supplier handoff", FaBoxOpen],
  ["awaiting_pickup", "Awaiting pickup", FaTruckLoading],
  ["pickup_assigned", "Pickup assigned", FaClipboardList],
  ["picked_up", "Picked up", FaShippingFast],
  ["in_transit", "In transit", FaRoute],
  ["out_for_delivery", "Out for delivery", FaClock],
  ["delivered_today", "Delivered today", FaCheckCircle],
  ["failed_deliveries", "Failed deliveries", FaExclamationTriangle],
  ["attempts_today", "Attempts today", FaBell],
  ["current_workload", "Current workload", FaTruckLoading],
  ["active_returns", "Active returns", FaRedoAlt],
];

function formatTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async (silent = false) => {
    if (silent) setRefreshing(true);
    else setLoading(true);

    try {
      setError("");
      const result = await getDashboard();
      setData(result);
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to load logistics dashboard.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // Initial load is intentionally performed in the effect; the callback owns async state reconciliation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDashboard();
    const interval = window.setInterval(() => loadDashboard(true), 15000);
    return () => window.clearInterval(interval);
  }, [loadDashboard]);

  const metrics = data?.metrics || {};
  const alerts = data?.recent_alerts || [];

  return (
    <section className="dashboard-page">
      <div className="dashboard-header">
        <div>
          <div className="dashboard-kicker">TODAY'S OPERATIONS</div>
          <h1>Logistics dashboard</h1>
          <p>
            One workspace for supplier handoff, pickup, shipment and last-mile
            operations.
          </p>
        </div>
        <button
          type="button"
          className="dashboard-refresh"
          onClick={() => loadDashboard(true)}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <div className="dashboard-error">{error}</div>}

      <div className="dashboard-grid">
        {metricCards.map(([key, label, Icon]) => (
          <div className={`metric-card metric-${key}`} key={key}>
            <div className="metric-icon">
              <Icon />
            </div>
            <div>
              <span>{label}</span>
              <strong>{loading ? "—" : (metrics[key] ?? 0)}</strong>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-columns">
        <section className="dashboard-panel">
          <div className="dashboard-panel-head">
            <div>
              <h2>Current workload</h2>
              <p>Orders that still need an operational action.</p>
            </div>
            <Link to="/queue">Open queue</Link>
          </div>

          <div className="workload-row">
            <div>
              <span>Active workload</span>
              <strong>{loading ? "—" : (metrics.current_workload ?? 0)}</strong>
            </div>
            <div>
              <span>Unread alerts</span>
              <strong>{loading ? "—" : (metrics.unread_alerts ?? 0)}</strong>
            </div>
            <div>
              <span>Failed deliveries</span>
              <strong>
                {loading ? "—" : (metrics.failed_deliveries ?? 0)}
              </strong>
            </div>
          </div>

          <div className="dashboard-callout">
            <FaBell />
            <div>
              <strong>Live operational alerts</strong>
              <span>
                Supplier handoff notifications and delivery issues are polled
                from the real backend state.
              </span>
            </div>
          </div>
        </section>

        <section className="dashboard-panel dashboard-alerts">
          <div className="dashboard-panel-head">
            <div>
              <h2>Recent alerts</h2>
              <p>Latest logistics notifications.</p>
            </div>
          </div>

          {alerts.length === 0 ? (
            <div className="dashboard-alert-empty">
              <FaBell />
              <span>No recent operational alerts.</span>
            </div>
          ) : (
            <div className="dashboard-alert-list">
              {alerts.map((alert) => (
                <div
                  className={`dashboard-alert ${alert.is_read ? "read" : "unread"}`}
                  key={alert.id}
                >
                  <div className="dashboard-alert-dot" />
                  <div>
                    <strong>{alert.title}</strong>
                    <span>{alert.message}</span>
                    <small>{formatTime(alert.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
