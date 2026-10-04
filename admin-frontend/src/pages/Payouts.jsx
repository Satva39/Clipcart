import { useEffect, useState } from "react";
import {
  getPayoutAccounts,
  getPayouts,
  updatePayoutStatus,
  verifyPayoutAccount,
} from "../services/payoutService";

function formatMoney(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

export default function Payouts() {
  const [status, setStatus] = useState("");
  const [payouts, setPayouts] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [verifyingId, setVerifyingId] = useState(null);
  const [error, setError] = useState("");

  async function loadPayouts() {
    try {
      setLoading(true);
      const result = await getPayouts(status);
      setPayouts(result);
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to load payout requests.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadAccounts() {
    try {
      setAccountsLoading(true);
      const result = await getPayoutAccounts();
      setAccounts(result);
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to load payout accounts.",
      );
    } finally {
      setAccountsLoading(false);
    }
  }

  useEffect(() => {
    loadPayouts();
  }, [status]);

  useEffect(() => {
    loadAccounts();
  }, []);

  async function update(id, next) {
    try {
      setError("");
      await updatePayoutStatus(id, next);
      await loadPayouts();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to update payout.");
    }
  }

  async function verify(id) {
    const confirmed = window.confirm(
      "Verify this supplier payout account? Confirm that the submitted account details have been reviewed.",
    );
    if (!confirmed) return;

    try {
      setVerifyingId(id);
      setError("");
      await verifyPayoutAccount(id);
      await loadAccounts();
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to verify payout account.",
      );
    } finally {
      setVerifyingId(null);
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header admin-page-header-row">
        <div>
          <span className="admin-eyebrow">SUPPLIER PAYOUT OPERATIONS</span>
          <h1>Payouts</h1>
          <p>
            Review supplier payout accounts and manage payout processing status.
          </p>
        </div>
        <select
          className="admin-status-select"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          <option>PENDING</option>
          <option>PROCESSING</option>
          <option>PAID</option>
          <option>FAILED</option>
        </select>
      </div>

      {error && <div className="admin-error">{error}</div>}

      <div className="admin-table-card" style={{ marginBottom: 24 }}>
        <div style={{ padding: "22px 22px 4px" }}>
          <span className="admin-eyebrow">PAYOUT ACCOUNT REVIEW</span>
          <h2 style={{ margin: "7px 0 5px" }}>Supplier payout accounts</h2>
          <p style={{ margin: 0, color: "#94a3b8" }}>
            Review the submitted payout details and approve an account before
            the supplier can request payouts.
          </p>
        </div>
        <div className="admin-table-wrap">
          {accountsLoading ? (
            <div className="admin-empty">Loading payout accounts…</div>
          ) : !accounts.length ? (
            <div className="admin-empty">
              No supplier payout accounts found.
            </div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th>Account holder</th>
                  <th>Bank / UPI</th>
                  <th>Account details</th>
                  <th>Verification</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td>
                      <strong>Supplier #{account.account_id}</strong>
                      <span>Payout account #{account.id}</span>
                    </td>
                    <td>{account.holder_name || "—"}</td>
                    <td>
                      <strong>{account.bank_name || "UPI"}</strong>
                      <span>{account.upi_id || "Bank payout"}</span>
                    </td>
                    <td>
                      <span>{account.account_number || "—"}</span>
                      <span>{account.ifsc || "—"}</span>
                    </td>
                    <td>
                      <span>
                        {account.is_verified ? "VERIFIED" : "PENDING"}
                      </span>
                    </td>
                    <td>
                      {account.is_verified ? (
                        <span>Verified</span>
                      ) : (
                        <button
                          type="button"
                          className="admin-primary-btn"
                          disabled={verifyingId === account.id}
                          onClick={() => verify(account.id)}
                        >
                          {verifyingId === account.id
                            ? "Verifying…"
                            : "Verify account"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="admin-table-card">
        <div style={{ padding: "22px 22px 4px" }}>
          <span className="admin-eyebrow">PAYOUT REQUESTS</span>
          <h2 style={{ margin: "7px 0 5px" }}>Supplier payouts</h2>
          <p style={{ margin: 0, color: "#94a3b8" }}>
            Operational payout status plus the account information required to
            execute supplier payouts. This section is restricted to authorized
            admins.
          </p>
        </div>
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading payouts…</div>
          ) : !payouts.length ? (
            <div className="admin-empty">No payout records found.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Payout</th>
                  <th>Supplier</th>
                  <th>Amount</th>
                  <th>Reference</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {payouts.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>#{r.id}</strong>
                      <span>Account #{r.payout_account_id}</span>
                    </td>
                    <td>Supplier #{r.account_id}</td>
                    <td>₹{formatMoney(r.amount)}</td>
                    <td>{r.reference_id || "—"}</td>
                    <td>
                      {r.status !== "PAID" ? (
                        <select
                          className="admin-status-select"
                          value={r.status}
                          onChange={(e) => update(r.id, e.target.value)}
                        >
                          <option value="PENDING">PENDING</option>
                          <option value="PROCESSING">PROCESSING</option>
                          <option value="FAILED">FAILED</option>
                          <option value="PAID">PAID</option>
                        </select>
                      ) : (
                        <span>PAID</span>
                      )}
                    </td>
                    <td>
                      {r.created_at
                        ? new Date(r.created_at).toLocaleString("en-IN")
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
