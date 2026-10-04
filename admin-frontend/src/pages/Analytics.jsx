import { useEffect, useState } from "react";
import { getAdminAnalytics } from "../services/analyticsService";

const metricLabels = {
  customers: "Customers",
  suppliers: "Suppliers",
  logistics_users: "Logistics users",
  products: "Products",
  active_products: "Active products",
  orders: "Orders",
  delivered_orders: "Delivered orders",
  revenue: "Revenue",
  payment_count: "Successful payments",
  payment_total: "Payment total",
  pending_payouts: "Pending payouts",
  paid_payouts: "Paid payouts",
};

export default function Analytics() {
  const now = new Date();
  const prior = new Date(now);
  prior.setDate(prior.getDate() - 89);
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
        const x = await getAdminAnalytics({ start_date: start, end_date: end });
        if (alive) setData(x);
      } catch (err) {
        if (alive)
          setError(err?.response?.data?.message || "Unable to load analytics.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [start, end]);
  const trend = data?.trend || [];
  const max = Math.max(1, ...trend.map((x) => Number(x.revenue || 0)));
  const chartMinWidth = Math.max(640, trend.length * 72);

  function growthValue(value) {
    return value == null ? "New" : `${Number(value).toLocaleString("en-IN")} %`;
  }
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">PLATFORM ANALYTICS</span>
        <h1>Analytics</h1>
        <p>Aggregate growth, payment and payout trends only.</p>
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
        <div className="admin-empty">Loading analytics…</div>
      ) : (
        data && (
          <>
            <div className="stats-grid">
              {Object.entries(data.summary || {}).map(([key, val]) => (
                <div className="stat-card" key={key}>
                  <div className="stat-icon">◆</div>
                  <div>
                    <span>{metricLabels[key] || key}</span>
                    <strong>
                      {[
                        "revenue",
                        "payment_total",
                        "pending_payouts",
                        "paid_payouts",
                      ].includes(key)
                        ? `₹${Number(val || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`
                        : Number(val || 0).toLocaleString("en-IN")}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
            <section className="admin-analytics-card">
              <div className="analytics-section-header">
                <h2>Period trend</h2>
                <p>Revenue buckets based on the selected date window.</p>
              </div>
              <div className="monthly-chart-scroll">
                <div
                  className="monthly-chart"
                  style={{
                    minWidth: `${chartMinWidth}px`,
                    gridTemplateColumns: `repeat(${Math.max(trend.length, 1)}, minmax(56px, 1fr))`,
                  }}
                >
                  {trend.map((b, i) => (
                    <div className="monthly-column" key={i}>
                      <div className="monthly-value">
                        ₹{Number(b.revenue || 0).toLocaleString("en-IN")}
                      </div>
                      <div className="monthly-bar-area">
                        <div
                          className="monthly-bar"
                          style={{
                            height: `${Math.max(3, (Number(b.revenue || 0) / max) * 100)}%`,
                          }}
                        />
                      </div>
                      <span>
                        {new Date(b.start).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                        })}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
            <div className="admin-detail-grid">
              <section className="admin-detail-card">
                <h2>Growth vs previous period</h2>
                <div className="admin-total-row">
                  <span>Orders</span>
                  <strong>{growthValue(data.growth?.orders_percent)}</strong>
                </div>
                <div className="admin-total-row">
                  <span>Revenue</span>
                  <strong>{growthValue(data.growth?.revenue_percent)}</strong>
                </div>
                <div className="admin-total-row">
                  <span>Customers</span>
                  <strong>{growthValue(data.growth?.customers_percent)}</strong>
                </div>
                <div className="admin-total-row">
                  <span>Suppliers</span>
                  <strong>{growthValue(data.growth?.suppliers_percent)}</strong>
                </div>
              </section>
              <section className="admin-detail-card">
                <h2>Privacy boundary</h2>
                <p>
                  Analytics never returns individual customer order histories,
                  addresses, supplier catalogs or other private transactional
                  records.
                </p>
              </section>
            </div>
          </>
        )
      )}
    </div>
  );
}
