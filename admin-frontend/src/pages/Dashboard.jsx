import { useEffect, useState } from "react";
import { getAdminDashboard } from "../services/dashboardService";

const cards = [
  ["Customers", "customers"],
  ["Suppliers", "suppliers"],
  ["Logistics users", "logistics_users"],
  ["Products", "products"],
  ["Active products", "active_products"],
  ["Total orders", "orders"],
  ["Total delivered", "delivered_orders"],
  ["All-time revenue", "revenue"],
  ["Payments in period", "payments"],
  ["Pending payouts", "pending_payouts"],
];

export default function Dashboard() {
  const now = new Date();
  const prior = new Date(now);
  prior.setDate(prior.getDate() - 29);
  const [start, setStart] = useState(prior.toISOString().slice(0, 10));
  const [end, setEnd] = useState(now.toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoading(true);
        setError("");
        const x = await getAdminDashboard({ start_date: start, end_date: end });
        if (alive) setData(x);
      } catch (err) {
        if (alive)
          setError(err?.response?.data?.message || "Unable to load dashboard.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [start, end]);

  const value = (key) => {
    const v = data?.totals?.[key] ?? data?.period_metrics?.[key];
    if (key === "revenue" || key === "payments" || key === "pending_payouts")
      return `₹${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
    return Number(v || 0).toLocaleString("en-IN");
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">PLATFORM OVERVIEW</span>
        <h1>Dashboard</h1>
        <p>
          Aggregate platform health without customer order-history exposure.
        </p>
      </div>
      <div className="admin-date-bar">
        <label>
          From{" "}
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label>
          To{" "}
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
      </div>
      {error && <div className="admin-error">{error}</div>}
      {loading ? (
        <div className="admin-empty">Loading platform metrics…</div>
      ) : (
        <>
          <div className="stats-grid">
            {cards.map(([label, key]) => (
              <div className="stat-card" key={key}>
                <div className="stat-icon">◆</div>
                <div>
                  <span>{label}</span>
                  <strong>{value(key)}</strong>
                </div>
              </div>
            ))}
          </div>
          <div className="admin-detail-grid">
            <section className="admin-detail-card">
              <h2>Growth</h2>
              <div className="admin-total-row">
                <span>Customers</span>
                <strong>{data?.growth?.customers_percent ?? 0}%</strong>
              </div>
              <div className="admin-total-row">
                <span>Suppliers</span>
                <strong>{data?.growth?.suppliers_percent ?? 0}%</strong>
              </div>
              <div className="admin-total-row">
                <span>Orders</span>
                <strong>{data?.growth?.orders_percent ?? 0}%</strong>
              </div>
            </section>
            <section className="admin-detail-card">
              <h2>Data boundary</h2>
              <p>
                Dashboard metrics are platform aggregates. Customer-specific
                order history and unrestricted supplier catalog data are
                intentionally excluded.
              </p>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
