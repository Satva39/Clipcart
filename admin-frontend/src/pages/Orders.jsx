import { useEffect, useState } from "react";
import { FaSearch, FaShoppingCart } from "react-icons/fa";

import { getAdminOrders } from "../services/orderService";

export default function Orders() {
  const [orders, setOrders] = useState([]);

  const [search, setSearch] = useState("");

  const [status, setStatus] = useState("");

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  async function loadOrders() {
    try {
      setLoading(true);
      setError("");

      const data = await getAdminOrders(search, status);

      setOrders(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load orders.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Status changes intentionally trigger the list refresh; search refresh remains Enter-driven.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadOrders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <span className="admin-eyebrow">PLATFORM MANAGEMENT</span>

          <h1>Orders</h1>

          <p>Monitor all Clipcart customer orders.</p>
        </div>

        <div className="admin-summary">
          <FaShoppingCart />
          {orders.length} orders
        </div>
      </div>

      {error && <div className="admin-error">{error}</div>}

      <div className="admin-toolbar">
        <div className="admin-search">
          <FaSearch />

          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                loadOrders();
              }
            }}
            placeholder="Search customer or email..."
          />
        </div>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="admin-status-select"
        >
          <option value="">All Status</option>

          <option value="PENDING">Pending</option>

          <option value="PROCESSING">Processing</option>

          <option value="SHIPPED">Shipped</option>

          <option value="DELIVERED">Delivered</option>

          <option value="CANCELLED">Cancelled</option>
        </select>

        <button
          type="button"
          onClick={loadOrders}
          className="admin-primary-btn"
        >
          Search
        </button>
      </div>

      <div className="admin-table-card">
        {loading ? (
          <div className="admin-empty">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="admin-empty">No orders found.</div>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Order</th>

                  <th>Customer</th>

                  <th>Items</th>

                  <th>Total</th>

                  <th>Status</th>

                  <th>Date</th>
                </tr>
              </thead>

              <tbody>
                {orders.map((order) => (
                  <tr
                    key={order.id}
                    className="admin-clickable-row"
                    onClick={() =>
                      (window.location.href = `/orders/${order.id}`)
                    }
                  >
                    <td>
                      <strong>#{order.id}</strong>
                    </td>

                    <td>
                      <strong>{order.customer}</strong>

                      <span>{order.customer_email}</span>
                    </td>

                    <td>{order.items}</td>

                    <td>₹{Number(order.total).toLocaleString("en-IN")}</td>

                    <td>
                      <span
                        className={`admin-order-status admin-order-${String(
                          order.status,
                        ).toLowerCase()}`}
                      >
                        {order.status}
                      </span>
                    </td>

                    <td>
                      {order.created_at
                        ? new Date(order.created_at).toLocaleDateString("en-IN")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
