import { useEffect, useState } from "react";
import {
  getCustomers,
  updateCustomerStatus,
} from "../services/customerService";

export default function Customers() {
  const [search, setSearch] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setLoading(true);
      setError("");
      setData(await getCustomers(search));
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load customers.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const id = setTimeout(load, 250);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  async function change(id, status) {
    try {
      await updateCustomerStatus(id, status);
      await load();
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to update account status.",
      );
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">ACCOUNT MANAGEMENT</span>
        <h1>Customers</h1>
        <p>
          Search permitted account data and manage access status. Shopping
          history is not exposed.
        </p>
      </div>
      <div className="admin-toolbar">
        <div className="admin-search">
          <span>⌕</span>
          <input
            placeholder="Search name, email or phone"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      {error && <div className="admin-error">{error}</div>}
      <div className="admin-table-card">
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading customers…</div>
          ) : !data?.customers?.length ? (
            <div className="admin-empty">No customers found.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Contact</th>
                  <th>Status</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {data.customers.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.full_name}</strong>
                      <span>#{c.id}</span>
                    </td>
                    <td>
                      <strong>{c.email}</strong>
                      <span>{c.phone || "No phone"}</span>
                    </td>
                    <td>
                      <select
                        className="admin-status-select"
                        value={c.status}
                        onChange={(e) => change(c.id, e.target.value)}
                      >
                        <option>ACTIVE</option>
                        <option>PENDING</option>
                        <option>SUSPENDED</option>
                      </select>
                    </td>
                    <td>
                      {c.created_at
                        ? new Date(c.created_at).toLocaleDateString("en-IN")
                        : "—"}
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
