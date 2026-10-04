import { useEffect, useState } from "react";
import {
  getSuppliers,
  updateSupplierStatus,
  updateSupplierVerification,
} from "../services/supplierService";

export default function Suppliers() {
  const [search, setSearch] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    try {
      setLoading(true);
      setError("");
      setData(await getSuppliers(search));
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load suppliers.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const id = setTimeout(load, 250);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);
  async function update(id, type, status) {
    try {
      type === "status"
        ? await updateSupplierStatus(id, status)
        : await updateSupplierVerification(id, status);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to update supplier.");
    }
  }
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">SUPPLIER OPERATIONS</span>
        <h1>Suppliers</h1>
        <p>
          Manage onboarding, account access and payout eligibility without
          browsing supplier catalogs.
        </p>
      </div>
      <div className="admin-toolbar">
        <div className="admin-search">
          <span>⌕</span>
          <input
            placeholder="Search supplier account or business"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      {error && <div className="admin-error">{error}</div>}
      <div className="admin-table-card">
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading suppliers…</div>
          ) : !data?.suppliers?.length ? (
            <div className="admin-empty">No suppliers found.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th>Business</th>
                  <th>Onboarding</th>
                  <th>Account</th>
                  <th>Payout</th>
                </tr>
              </thead>
              <tbody>
                {data.suppliers.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{s.full_name}</strong>
                      <span>{s.email}</span>
                    </td>
                    <td>
                      <strong>{s.business_name || "—"}</strong>
                      <span>{s.gst_number || "No GST supplied"}</span>
                    </td>
                    <td>
                      <span>
                        Fee: {s.registration_fee_paid ? "Paid" : "Pending"}
                      </span>
                      <select
                        className="admin-status-select"
                        value={s.registration_status}
                        onChange={(e) =>
                          update(s.id, "verification", e.target.value)
                        }
                      >
                        <option>PENDING</option>
                        <option>APPROVED</option>
                        <option>REJECTED</option>
                      </select>
                    </td>
                    <td>
                      <select
                        className="admin-status-select"
                        value={s.status}
                        onChange={(e) => update(s.id, "status", e.target.value)}
                      >
                        <option>ACTIVE</option>
                        <option>PENDING</option>
                        <option>SUSPENDED</option>
                      </select>
                    </td>
                    <td>
                      <strong>
                        {s.payout_eligible ? "Eligible" : "Not eligible"}
                      </strong>
                      <span>
                        {s.payout_account_verified
                          ? "Account verified"
                          : "Account unverified"}
                      </span>
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
