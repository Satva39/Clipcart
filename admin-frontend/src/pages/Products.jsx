import { useEffect, useState } from "react";
import {
  createAdminProduct,
  deactivateAdminProduct,
  getAdminProducts,
  getBrands,
  getCategories,
  updateAdminProduct,
} from "../services/productService";

const blank = {
  name: "",
  description: "",
  sku: "",
  category_id: "",
  brand_id: "",
  price: "",
  compare_price: "",
  stock: 0,
  low_stock_threshold: 5,
  status: "ACTIVE",
  is_featured: false,
};

export default function Products() {
  const [rows, setRows] = useState(null);
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(blank);
  const [editing, setEditing] = useState(null);
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    try {
      setLoading(true);
      setRows(await getAdminProducts(search));
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to load platform products.",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    Promise.all([getCategories(), getBrands()])
      .then(([c, b]) => {
        setCategories(c);
        setBrands(b);
      })
      .catch((err) =>
        setError(
          err?.response?.data?.message || "Unable to load catalog data.",
        ),
      );
  }, []);
  useEffect(() => {
    const id = setTimeout(load, 250);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);
  function edit(row) {
    setEditing(row.id);
    setForm({
      ...blank,
      ...row,
      category_id: row.category_id || "",
      brand_id: row.brand_id || "",
    });
    setShow(true);
  }
  async function submit(e) {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        category_id: Number(form.category_id),
        brand_id: form.brand_id ? Number(form.brand_id) : null,
        price: Number(form.price),
        compare_price:
          form.compare_price === "" ? null : Number(form.compare_price),
        stock: Number(form.stock),
        low_stock_threshold: Number(form.low_stock_threshold),
      };
      if (editing) await updateAdminProduct(editing, payload);
      else await createAdminProduct(payload);
      setShow(false);
      setEditing(null);
      setForm(blank);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to save product.");
    }
  }
  async function deactivate(id) {
    try {
      await deactivateAdminProduct(id);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to deactivate product.");
    }
  }
  return (
    <div className="admin-page">
      <div className="admin-page-header admin-page-header-row">
        <div>
          <span className="admin-eyebrow">PLATFORM CATALOG</span>
          <h1>Platform products</h1>
          <p>
            Only products owned by the private platform admin are shown here.
          </p>
        </div>
        <button
          className="admin-primary-btn"
          onClick={() => {
            setEditing(null);
            setForm(blank);
            setShow(true);
          }}
        >
          + Add product
        </button>
      </div>
      {show && (
        <form className="admin-form-card" onSubmit={submit}>
          <div className="admin-form-grid">
            <label>
              Name
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </label>
            <label>
              SKU
              <input
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
                required
              />
            </label>
            <label>
              Category
              <select
                value={form.category_id}
                onChange={(e) =>
                  setForm({ ...form, category_id: e.target.value })
                }
                required
              >
                <option value="">Select category</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Brand
              <select
                value={form.brand_id || ""}
                onChange={(e) => setForm({ ...form, brand_id: e.target.value })}
              >
                <option value="">No brand</option>
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Price
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                required
              />
            </label>
            <label>
              Compare price
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.compare_price ?? ""}
                onChange={(e) =>
                  setForm({ ...form, compare_price: e.target.value })
                }
              />
            </label>
            <label>
              Stock
              <input
                type="number"
                min="0"
                value={form.stock}
                onChange={(e) => setForm({ ...form, stock: e.target.value })}
              />
            </label>
            <label>
              Low-stock threshold
              <input
                type="number"
                min="0"
                value={form.low_stock_threshold}
                onChange={(e) =>
                  setForm({ ...form, low_stock_threshold: e.target.value })
                }
              />
            </label>
            <label>
              Status
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option>ACTIVE</option>
                <option>INACTIVE</option>
                <option>PENDING_REVIEW</option>
                <option>REJECTED</option>
              </select>
            </label>
            <label>
              Featured
              <select
                value={form.is_featured ? "true" : "false"}
                onChange={(e) =>
                  setForm({ ...form, is_featured: e.target.value === "true" })
                }
              >
                <option value="false">No</option>
                <option value="true">Yes</option>
              </select>
            </label>
            <label className="wide-field">
              Description
              <textarea
                rows="4"
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                required
              />
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="admin-primary-btn">
              {editing ? "Save changes" : "Create product"}
            </button>
            <button
              type="button"
              className="admin-secondary-btn"
              onClick={() => setShow(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      <div className="admin-toolbar">
        <div className="admin-search">
          <span>⌕</span>
          <input
            placeholder="Search platform products"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      {error && <div className="admin-error">{error}</div>}
      <div className="admin-table-card">
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading products…</div>
          ) : !rows?.products?.length ? (
            <div className="admin-empty">No platform products found.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Moderation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.products.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.name}</strong>
                      <span>{r.sku}</span>
                    </td>
                    <td>₹{Number(r.price).toLocaleString("en-IN")}</td>
                    <td>{r.stock}</td>
                    <td>
                      <span>{r.status}</span>
                      {r.is_featured && <span>Featured</span>}
                    </td>
                    <td>
                      <button
                        className="admin-small-btn"
                        onClick={() => edit(r)}
                      >
                        Edit
                      </button>
                      <button
                        className="admin-danger-btn"
                        onClick={() => deactivate(r.id)}
                      >
                        Deactivate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
