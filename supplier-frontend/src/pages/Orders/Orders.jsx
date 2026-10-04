import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  FaChevronLeft,
  FaChevronRight,
  FaDownload,
  FaFileUpload,
  FaSearch,
  FaShoppingCart,
} from "react-icons/fa";
import {
  getSupplierOrders,
  importSupplierOrders,
} from "../../services/orderService";
import { formatDateTime, money } from "../../utils/dateRange";
import { downloadSupplierExport } from "../../services/portalService";
import "../../styles/supplier-pages.css";

export default function Orders() {
  const [data, setData] = useState({
    orders: [],
    pagination: { page: 1, pages: 0, total: 0 },
  });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [importing, setImporting] = useState(false);
  const fileRef = useRef(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setError("");
      setData(await getSupplierOrders({ search, status, page, per_page: 20 }));
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load orders.");
    } finally {
      setLoading(false);
    }
  }, [search, status, page]);
  useEffect(() => {
    load();
  }, [load]);
  function changeStatus(next) {
    setStatus(next);
    setPage(1);
  }

  async function handleImport(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    setNotice("");
    setImporting(true);
    try {
      const result = await importSupplierOrders(file);
      const imported = result?.data || {};
      setNotice(
        `Imported ${imported.updated || 0} order${imported.updated === 1 ? "" : "s"}. ${imported.unchanged || 0} already processing.`,
      );
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to import orders CSV.");
    } finally {
      setImporting(false);
    }
  }

  async function handleExport() {
    setError("");
    setNotice("");
    try {
      await downloadSupplierExport("orders");
      setNotice("Orders CSV exported.");
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to export orders CSV.");
    }
  }

  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Orders</h2>
          <p>
            Orders containing your products. Customer delivery details are shown
            only on fulfillment screens.
          </p>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      {notice && <div className="notice success">{notice}</div>}
      <section className="panel">
        <div className="toolbar supplier-orders-toolbar">
          <div className="toolbar-left">
            <div className="search-control">
              <FaSearch />
              <input
                className="toolbar-input"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search order ID or product…"
                aria-label="Search supplier orders"
              />
            </div>
            <select
              className="toolbar-select"
              value={status}
              onChange={(e) => changeStatus(e.target.value)}
            >
              <option value="">All statuses</option>
              <option value="PAID">Paid</option>
              <option value="PROCESSING">Processing</option>
              <option value="SHIPPED">Shipped</option>
              <option value="OUT_FOR_DELIVERY">Out for delivery</option>
              <option value="DELIVERED">Delivered</option>
              <option value="CANCELLED">Cancelled</option>
              <option value="RETURNED">Returned</option>
            </select>
          </div>
          <div className="supplier-orders-actions">
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={handleImport}
            />
            <button
              type="button"
              className="ghost-link supplier-csv-btn"
              onClick={() => fileRef.current?.click()}
              disabled={importing}
            >
              <FaFileUpload /> {importing ? "Importing…" : "Import CSV"}
            </button>
            <button
              type="button"
              className="ghost-link supplier-csv-btn"
              onClick={handleExport}
            >
              <FaDownload /> Export CSV
            </button>
            <span className="muted">{data.pagination?.total || 0} orders</span>
          </div>
        </div>
        {loading ? (
          <div className="table-skeleton">Loading orders…</div>
        ) : data.orders?.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Products</th>
                  <th>Customer</th>
                  <th>Supplier total</th>
                  <th>Units</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.orders.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <Link to={`/orders/${o.id}`} className="table-link">
                        #{o.id}
                      </Link>
                    </td>
                    <td>
                      <div className="supplier-order-product-previews">
                        {(o.product_previews || []).map((product) => (
                          <span
                            className="supplier-order-product-preview"
                            key={`${product.product_id}-${product.variant_value || "base"}`}
                            title={`${product.product_name}${product.variant_value ? ` · ${product.variant_value}` : ""}`}
                          >
                            {product.image ? (
                              <img
                                src={product.image}
                                alt=""
                                loading="lazy"
                                onError={(event) => {
                                  event.currentTarget.style.display = "none";
                                  event.currentTarget.nextElementSibling.style.display =
                                    "grid";
                                }}
                              />
                            ) : null}
                            <FaShoppingCart
                              style={{
                                display: product.image ? "none" : "grid",
                              }}
                            />
                          </span>
                        ))}
                        {!o.product_previews?.length && (
                          <span className="muted">—</span>
                        )}
                      </div>
                    </td>
                    <td>{o.customer || "—"}</td>
                    <td>{money(o.total)}</td>
                    <td>{o.items}</td>
                    <td>
                      <Status status={o.status} />
                    </td>
                    <td>{formatDateTime(o.created_at)}</td>
                    <td>
                      <Link to={`/orders/${o.id}`} className="ghost-link">
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <FaShoppingCart />
            <h3>No supplier orders</h3>
            <p>
              New customer orders containing your products will appear here.
            </p>
          </div>
        )}
        <div className="pagination">
          <button
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            aria-label="Previous page"
          >
            <FaChevronLeft />
          </button>
          <span>
            Page {page} of {Math.max(data.pagination?.pages || 0, 1)}
          </span>
          <button
            disabled={!data.pagination?.pages || page >= data.pagination.pages}
            onClick={() => setPage(page + 1)}
            aria-label="Next page"
          >
            <FaChevronRight />
          </button>
        </div>
      </section>
    </div>
  );
}
function Status({ status }) {
  const good = status === "DELIVERED";
  const danger = ["CANCELLED", "RETURNED"].includes(status);
  return (
    <span
      className={`status-chip ${good ? "success" : danger ? "danger" : "warning"}`}
    >
      {status}
    </span>
  );
}
