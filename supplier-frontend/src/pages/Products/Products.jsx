import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FaBoxOpen,
  FaChevronLeft,
  FaChevronRight,
  FaDownload,
  FaEdit,
  FaPlus,
  FaSearch,
  FaToggleOff,
  FaToggleOn,
} from "react-icons/fa";
import {
  getSupplierCatalog,
  deleteSupplierProduct,
  updateSupplierProduct,
} from "../../services/productService";
import { downloadSupplierExport } from "../../services/portalService";
import "../../styles/supplier-pages.css";

export default function Products() {
  const [data, setData] = useState({
    products: [],
    pagination: { page: 1, pages: 0, total: 0 },
  });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setError("");
      setData(await getSupplierCatalog({ search, status, page, per_page: 15 }));
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load products.");
    } finally {
      setLoading(false);
    }
  }, [search, status, page]);
  useEffect(() => {
    load();
  }, [load]);
  async function toggle(p) {
    setWorking(p.id);
    try {
      await updateSupplierProduct(p.id, {
        status: p.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
      });
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to update product.");
    } finally {
      setWorking(null);
    }
  }
  async function remove(p) {
    if (
      !window.confirm(
        `Delete ${p.name} permanently? Products with existing order history cannot be permanently deleted.`,
      )
    )
      return;
    setWorking(p.id);
    try {
      await deleteSupplierProduct(p.id);
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to delete product.");
    } finally {
      setWorking(null);
    }
  }
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Products</h2>
          <p>
            Manage listings, pricing, variants, media and live availability.
          </p>
        </div>
        <div className="heading-actions">
          <button
            className="ghost-link"
            onClick={() => downloadSupplierExport("products")}
          >
            <FaDownload /> Export CSV
          </button>
          <Link className="action-link" to="/products/add">
            <FaPlus /> Add product
          </Link>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      <section className="panel">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-control">
              <FaSearch />
              <input
                className="toolbar-input"
                placeholder="Search by product or SKU…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <select
              className="toolbar-select"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All status</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </div>
          <span className="muted">{data.pagination?.total || 0} products</span>
        </div>
        {loading ? (
          <div className="table-skeleton">Loading products…</div>
        ) : data.products?.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.products.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="product-cell">
                        <div className="product-thumb">
                          {p.image ? (
                            <img
                              src={p.image}
                              alt=""
                              loading="lazy"
                              decoding="async"
                            />
                          ) : (
                            <FaBoxOpen />
                          )}
                        </div>
                        <div>
                          <b>{p.name}</b>
                          <small>
                            {p.variant_count || 0} variants ·{" "}
                            {p.brand || "No brand"}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>{p.sku || "—"}</td>
                    <td>{p.category || "—"}</td>
                    <td>{`₹${Number(p.price || 0).toLocaleString("en-IN")}`}</td>
                    <td>
                      {p.stock}
                      <small>
                        {p.variant_count ? " base stock + variants" : ""}
                      </small>
                    </td>
                    <td>
                      <span
                        className={`status-chip ${p.status === "ACTIVE" ? "success" : "neutral"}`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <Link
                          to={`/products/${p.id}/edit`}
                          className="icon-btn"
                          aria-label="Edit product"
                        >
                          <FaEdit />
                        </Link>
                        <button
                          className="icon-btn"
                          disabled={working === p.id}
                          onClick={() => toggle(p)}
                          aria-label={
                            p.status === "ACTIVE" ? "Deactivate" : "Activate"
                          }
                        >
                          {p.status === "ACTIVE" ? (
                            <FaToggleOn />
                          ) : (
                            <FaToggleOff />
                          )}
                        </button>
                        <button
                          className="icon-btn danger-btn"
                          disabled={working === p.id}
                          onClick={() => remove(p)}
                          aria-label="Delete product"
                          title="Delete product"
                        >
                          ×
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <FaBoxOpen />
            <h3>No products found</h3>
            <p>Add your first product or adjust the search/status filters.</p>
            <Link className="action-link" to="/products/add">
              Add product
            </Link>
          </div>
        )}
        <div className="pagination">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            <FaChevronLeft />
          </button>
          <span>
            Page {page} of {Math.max(data.pagination?.pages || 0, 1)}
          </span>
          <button
            disabled={!data.pagination?.pages || page >= data.pagination.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <FaChevronRight />
          </button>
        </div>
      </section>
    </div>
  );
}
