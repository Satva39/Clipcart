import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaChartLine,
  FaBoxes,
  FaExchangeAlt,
  FaPercent,
  FaRupeeSign,
  FaShoppingCart,
  FaWallet,
} from "react-icons/fa";
import DateRangeControls from "../../components/DateRangeControls";
import { getSupplierAnalytics } from "../../services/portalService";
import { money } from "../../utils/dateRange";
import "../../styles/supplier-pages.css";

export default function Analytics() {
  const [range, setRange] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async (r) => {
    setLoading(true);
    setError("");
    try {
      setData(await getSupplierAnalytics(r));
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load analytics.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (range) load(range);
  }, [range, load]);
  const maxSales = useMemo(
    () => Math.max(...(data?.series || []).map((x) => Number(x.sales || 0)), 1),
    [data],
  );
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Analytics</h2>
          <p>
            Backend-derived supplier performance, product and stock analytics.
          </p>
        </div>
        <DateRangeControls onChange={setRange} />
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
          <div className="metric-grid analytics-metrics">
            <Metric
              icon={FaRupeeSign}
              label="Sales"
              value={money(data?.summary?.sales)}
            />
            <Metric
              icon={FaShoppingCart}
              label="Orders"
              value={data?.summary?.orders}
            />
            <Metric
              icon={FaBoxes}
              label="Units sold"
              value={data?.summary?.units_sold}
            />
            <Metric
              icon={FaRupeeSign}
              label="Average order value"
              value={money(data?.summary?.average_order_value)}
            />
            <Metric
              icon={FaPercent}
              label="Cancellation rate"
              value={`${data?.summary?.cancellation_rate || 0}%`}
            />
            <Metric
              icon={FaPercent}
              label="Return rate"
              value={`${data?.summary?.return_rate || 0}%`}
            />
            <Metric
              icon={FaChartLine}
              label="Cancelled orders"
              value={data?.summary?.cancelled_orders || 0}
            />
            <Metric
              icon={FaWallet}
              label="Returned orders"
              value={data?.summary?.returned_orders || 0}
            />
          </div>
          <section className="panel analytics-chart">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Sales trend</h3>
                <p className="panel-subtitle">
                  Daily supplier sales in the selected period.
                </p>
              </div>
              <span className="chart-total">{money(data?.summary?.sales)}</span>
            </div>
            <div className="bar-chart">
              {(data?.series || []).map((row) => (
                <div
                  className="bar-column"
                  key={row.date}
                  title={`${row.date}: ${money(row.sales)}`}
                >
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{
                        height: `${Math.max(3, (Number(row.sales || 0) / maxSales) * 100)}%`,
                      }}
                    />
                  </div>
                  <small>
                    {new Date(`${row.date}T00:00:00`).toLocaleDateString(
                      "en-IN",
                      { day: "2-digit", month: "short" },
                    )}
                  </small>
                </div>
              ))}
            </div>
          </section>
          <div className="two-panel-grid">
            <ProductTable
              title="Top products"
              rows={data?.top_products || []}
              positive
            />
            <ProductTable
              title="Low-performing products"
              rows={data?.low_performing_products || []}
            />
          </div>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Stock movement</h3>
                <p className="panel-subtitle">
                  Supplier-owned inventory adjustments recorded by the backend.
                </p>
              </div>
            </div>
            {data?.stock_movement?.length ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Variant</th>
                      <th>Change</th>
                      <th>Reason</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.stock_movement.map((row) => (
                      <tr key={row.id}>
                        <td>{row.product_name}</td>
                        <td>{row.variant || "Base stock"}</td>
                        <td
                          className={row.change > 0 ? "stock-up" : "stock-down"}
                        >
                          {row.change > 0 ? `+${row.change}` : row.change}
                        </td>
                        <td>{row.reason}</td>
                        <td>
                          {row.created_at
                            ? new Date(row.created_at).toLocaleString("en-IN")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <FaExchangeAlt />
                <h3>No stock movement</h3>
                <p>Inventory changes in this period will appear here.</p>
              </div>
            )}
          </section>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Payout history</h3>
                <p className="panel-subtitle">
                  Your supplier payout records only.
                </p>
              </div>
            </div>
            {data?.payout_history?.length ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Reference</th>
                      <th>Created</th>
                      <th>Processed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.payout_history.map((p) => (
                      <tr key={p.id}>
                        <td>{money(p.amount)}</td>
                        <td>
                          <span
                            className={`status-chip ${p.status === "PAID" ? "success" : p.status === "FAILED" ? "danger" : "warning"}`}
                          >
                            {p.status}
                          </span>
                        </td>
                        <td>{p.reference_id || "—"}</td>
                        <td>
                          {p.created_at
                            ? new Date(p.created_at).toLocaleDateString("en-IN")
                            : "—"}
                        </td>
                        <td>
                          {p.processed_at
                            ? new Date(p.processed_at).toLocaleDateString(
                                "en-IN",
                              )
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <FaWallet />
                <h3>No payouts recorded</h3>
                <p>Processed payout activity will appear here.</p>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
function Metric({ icon: Icon, label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">
        <Icon />
      </div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
function ProductTable({ title, rows }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">{title}</h3>
          <p className="panel-subtitle">Based on supplier-owned order items.</p>
        </div>
      </div>
      {rows.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Units</th>
                <th>Orders</th>
                <th>Revenue</th>
                <th>Stock</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <b>{r.name}</b>
                  </td>
                  <td>{r.units || 0}</td>
                  <td>{r.orders || 0}</td>
                  <td>{money(r.revenue)}</td>
                  <td>{r.stock ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <h3>No product data</h3>
          <p>Product performance will appear when orders are available.</p>
        </div>
      )}
    </section>
  );
}
