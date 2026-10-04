import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FaArrowRight,
  FaBell,
  FaBoxOpen,
  FaChartLine,
  FaClock,
  FaExclamationTriangle,
  FaRupeeSign,
  FaShoppingCart,
  FaTruck,
  FaWallet,
} from "react-icons/fa";
import DateRangeControls from "../../components/DateRangeControls";
import { getSupplierDashboard } from "../../services/portalService";
import { formatDateTime, money } from "../../utils/dateRange";
import "../../styles/supplier-pages.css";

const cards = [
  ["total_sales", "Sales", FaRupeeSign],
  ["order_count", "Orders", FaShoppingCart],
  ["pending_orders", "Pending orders", FaClock],
  ["delivered_orders", "Delivered", FaTruck],
  ["product_count", "Products", FaBoxOpen],
  ["active_product_count", "Active products", FaChartLine],
  ["low_stock_count", "Low stock", FaExclamationTriangle],
  ["available_payout", "Available payout", FaWallet],
];

export default function Dashboard() {
  const [range, setRange] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async (r) => {
    try {
      setLoading(true);
      setError("");
      setData(await getSupplierDashboard(r));
    } catch (e) {
      setError(
        e?.response?.data?.message || "Unable to load supplier dashboard.",
      );
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (range) load(range);
  }, [range, load]);
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Dashboard</h2>
          <p>
            Operational health, sales and fulfillment for your supplier account.
          </p>
        </div>
        <div className="heading-actions">
          <DateRangeControls onChange={setRange} compact />
          <Link className="action-link" to="/products/add">
            + Add product
          </Link>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 8 }, (_, i) => (
            <div className="skeleton" key={i} />
          ))}
        </div>
      ) : (
        <>
          <div className="metric-grid">
            {cards.map(([key, label, Icon]) => (
              <div className="metric-card" key={key}>
                <div className="metric-icon">
                  <Icon />
                </div>
                <div>
                  <span>{label}</span>
                  <strong>
                    {key.includes("sales") || key.includes("payout")
                      ? money(data?.metrics?.[key])
                      : (data?.metrics?.[key] ?? 0).toLocaleString("en-IN")}
                  </strong>
                </div>
              </div>
            ))}
          </div>
          <div className="dashboard-grid-pro">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">Recent orders</h3>
                  <p className="panel-subtitle">
                    Latest fulfillment work in the selected range.
                  </p>
                </div>
                <Link className="ghost-link" to="/orders">
                  View all <FaArrowRight />
                </Link>
              </div>
              {data?.recent_orders?.length ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Order</th>
                        <th>Customer</th>
                        <th>Status</th>
                        <th>Items</th>
                        <th>Supplier sales</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_orders.map((o) => (
                        <tr key={o.id}>
                          <td>
                            <Link to={`/orders/${o.id}`} className="table-link">
                              #{o.id}
                            </Link>
                          </td>
                          <td>{o.customer_name || "—"}</td>
                          <td>
                            <span
                              className={`status-chip ${o.status === "DELIVERED" ? "success" : o.status === "CANCELLED" || o.status === "RETURNED" ? "danger" : "warning"}`}
                            >
                              {o.status}
                            </span>
                          </td>
                          <td>{o.items}</td>
                          <td>{money(o.supplier_total)}</td>
                          <td>{formatDateTime(o.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">
                  <FaShoppingCart />
                  <h3>No orders in this range</h3>
                  <p>New customer orders will appear here automatically.</p>
                </div>
              )}
            </section>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">Notifications</h3>
                  <p className="panel-subtitle">
                    Order, stock and payout notices.
                  </p>
                </div>
                <Link className="ghost-link" to="/notifications">
                  Open inbox
                </Link>
              </div>
              {data?.recent_notifications?.length ? (
                <div className="notification-preview">
                  {data.recent_notifications.slice(0, 6).map((n) => (
                    <Link
                      key={n.id}
                      to="/notifications"
                      className={`notification-preview-row ${n.is_read ? "" : "unread"}`}
                    >
                      <div className="notification-icon">
                        <FaBell />
                      </div>
                      <div>
                        <strong>{n.title}</strong>
                        <p>{n.message}</p>
                        <small>{formatDateTime(n.created_at)}</small>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <FaBell />
                  <h3>All clear</h3>
                  <p>No supplier notifications yet.</p>
                </div>
              )}
            </section>
          </div>
          <div className="quick-actions">
            <Link to="/products/add" className="quick-action">
              <span>+</span>
              <div>
                <b>Add a product</b>
                <small>Create a listing with variants and media.</small>
              </div>
              <FaArrowRight />
            </Link>
            <Link to="/inventory" className="quick-action">
              <span>
                <FaWarehouseIcon />
              </span>
              <div>
                <b>Review stock</b>
                <small>Adjust inventory and clear low-stock alerts.</small>
              </div>
              <FaArrowRight />
            </Link>
            <Link to="/earnings" className="quick-action">
              <span>
                <FaWallet />
              </span>
              <div>
                <b>Manage payouts</b>
                <small>View earnings and payout status.</small>
              </div>
              <FaArrowRight />
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
function FaWarehouseIcon() {
  return <FaBoxOpen />;
}
