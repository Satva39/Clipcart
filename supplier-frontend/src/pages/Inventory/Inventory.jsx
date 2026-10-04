import { useCallback, useEffect, useState } from "react";
import {
  FaBoxes,
  FaChevronUp,
  FaExclamationTriangle,
  FaHistory,
  FaPlus,
  FaMinus,
} from "react-icons/fa";
import {
  adjustSupplierStock,
  getInventoryAlerts,
  getInventoryHistory,
  getSupplierInventory,
} from "../../services/inventoryService";
import "../../styles/supplier-pages.css";

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [alerts, setAlerts] = useState({ low_stock: [], out_of_stock: [] });
  const [expanded, setExpanded] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([
        getSupplierInventory(),
        getInventoryAlerts(),
      ]);
      setItems(a);
      setAlerts(b);
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load inventory.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  async function adjust(productId, variantId, amount) {
    if (!amount) return;
    setSaving(`${productId}:${variantId || 0}`);
    try {
      await adjustSupplierStock(productId, amount, "MANUAL_ADJUSTMENT", {
        variantId,
      });
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to update stock.");
    } finally {
      setSaving(null);
    }
  }
  async function showHistory(id) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    try {
      setHistory(await getInventoryHistory(id));
      setExpanded(id);
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load stock history.");
    }
  }
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Inventory</h2>
          <p>
            Adjust product or variant stock, review movement and monitor
            low-stock alerts.
          </p>
        </div>
        <div className="inventory-alert-summary">
          <span>
            <b>{alerts.low_stock?.length || 0}</b> low stock
          </span>
          <span>
            <b>{alerts.out_of_stock?.length || 0}</b> out of stock
          </span>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      <section className="inventory-alerts">
        <Alert
          title="Low stock"
          count={alerts.low_stock?.length || 0}
          items={alerts.low_stock || []}
          warning
        />
        <Alert
          title="Out of stock"
          count={alerts.out_of_stock?.length || 0}
          items={alerts.out_of_stock || []}
        />
      </section>
      <section className="panel">
        {loading ? (
          <div className="empty-state">Loading inventory…</div>
        ) : items.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Stock</th>
                  <th>Threshold</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <ProductRow
                    key={p.id}
                    p={p}
                    expanded={expanded === p.id}
                    saving={saving}
                    onAdjust={adjust}
                    onHistory={showHistory}
                    history={expanded === p.id ? history : []}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <FaBoxes />
            <h3>Inventory is empty</h3>
            <p>Add a product to start managing stock.</p>
          </div>
        )}
      </section>
    </div>
  );
}
function ProductRow({ p, expanded, saving, onAdjust, onHistory, history }) {
  const key = `${p.id}:0`;
  return (
    <>
      <tr>
        <td>
          <div className="inventory-product-cell">
            <span className="inventory-product-image">
              {p.image ? (
                <img
                  src={p.image}
                  alt=""
                  loading="lazy"
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                    event.currentTarget.nextElementSibling.style.display =
                      "grid";
                  }}
                />
              ) : null}
              <FaBoxes style={{ display: p.image ? "none" : "grid" }} />
            </span>
            <span>
              <b>{p.name}</b>
              {p.variant_count ? (
                <small className="table-sub">
                  {p.variant_count} variant{p.variant_count > 1 ? "s" : ""}
                </small>
              ) : null}
            </span>
          </div>
        </td>
        <td>{p.sku || "—"}</td>
        <td>
          <b>{p.variants?.length ? "Variant stock" : p.stock}</b>
        </td>
        <td>{p.low_stock_threshold}</td>
        <td>
          <span
            className={`status-chip ${p.stock_status === "IN_STOCK" ? "success" : p.stock_status === "OUT_OF_STOCK" ? "danger" : "warning"}`}
          >
            {p.stock_status?.replaceAll("_", " ")}
          </span>
        </td>
        <td>
          <div className="row-actions">
            <button
              className="icon-btn"
              onClick={() => onHistory(p.id)}
              aria-label="Show stock history"
            >
              {expanded ? <FaChevronUp /> : <FaHistory />}
            </button>
            {!p.variants?.length && (
              <>
                <button
                  disabled={saving === key}
                  className="icon-btn"
                  onClick={() => onAdjust(p.id, null, 1)}
                  aria-label="Increase stock"
                >
                  <FaPlus />
                </button>
                <button
                  disabled={saving === key}
                  className="icon-btn"
                  onClick={() => onAdjust(p.id, null, -1)}
                  aria-label="Decrease stock"
                >
                  <FaMinus />
                </button>
              </>
            )}
          </div>
        </td>
      </tr>
      {p.variants?.length
        ? p.variants.map((v) => (
            <tr key={`${p.id}-${v.id}`} className="variant-row">
              <td className="variant-name">
                ↳ {v.name}: {v.value}
              </td>
              <td>{v.sku}</td>
              <td>
                <b>{v.stock}</b>
              </td>
              <td>{p.low_stock_threshold}</td>
              <td>
                <span
                  className={`status-chip ${v.status === "IN_STOCK" ? "success" : v.status === "OUT_OF_STOCK" ? "danger" : "warning"}`}
                >
                  {v.status.replaceAll("_", " ")}
                </span>
              </td>
              <td>
                <div className="row-actions">
                  <button
                    disabled={saving === `${p.id}:${v.id}`}
                    className="icon-btn"
                    onClick={() => onAdjust(p.id, v.id, 1)}
                    aria-label="Increase variant stock"
                  >
                    <FaPlus />
                  </button>
                  <button
                    disabled={saving === `${p.id}:${v.id}`}
                    className="icon-btn"
                    onClick={() => onAdjust(p.id, v.id, -1)}
                    aria-label="Decrease variant stock"
                  >
                    <FaMinus />
                  </button>
                </div>
              </td>
            </tr>
          ))
        : null}
      {expanded && (
        <tr>
          <td colSpan="6">
            <div className="history-panel">
              <b>Recent movement</b>
              {history.length ? (
                <div>
                  {history.slice(0, 10).map((h) => (
                    <div className="history-line" key={h.id}>
                      <span>{h.variant || "Base stock"}</span>
                      <strong
                        className={h.change > 0 ? "stock-up" : "stock-down"}
                      >
                        {h.change > 0 ? `+${h.change}` : h.change}
                      </strong>
                      <small>
                        {h.reason} ·{" "}
                        {h.created_at
                          ? new Date(h.created_at).toLocaleString("en-IN")
                          : "—"}
                      </small>
                    </div>
                  ))}
                </div>
              ) : (
                <p>No movement recorded.</p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
function Alert({ title, count, items, warning }) {
  return (
    <div className={`alert-card ${warning ? "warning" : "danger"}`}>
      <FaExclamationTriangle />
      <div>
        <b>{title}</b>
        <span>
          {count} item{count === 1 ? "" : "s"}
        </span>
      </div>
      {items.slice(0, 2).map((x) => (
        <small key={`${x.product_id}-${x.variant_id || 0}`}>
          {x.product_name}
          {x.variant ? ` · ${x.variant}` : ""} · {x.stock} left
        </small>
      ))}
    </div>
  );
}
