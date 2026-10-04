import { useEffect, useState } from "react";
import { FaExclamationTriangle, FaWallet } from "react-icons/fa";
import {
  getPayoutAccount,
  getPayoutBalance,
  getPayoutHistory,
  requestPayout,
  savePayoutAccount,
} from "../../services/payoutService";
import { getSupplierEarnings } from "../../services/earningsService";
import { money } from "../../utils/dateRange";
import "../../styles/supplier-pages.css";

export default function Earnings() {
  const [earnings, setEarnings] = useState(null);
  const [account, setAccount] = useState(null);
  const [balance, setBalance] = useState(0);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [payoutAmount, setPayoutAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    holder_name: "",
    bank_name: "",
    account_number: "",
    ifsc: "",
    upi_id: "",
  });
  async function load() {
    setLoading(true);
    try {
      const [e, a, b, h] = await Promise.all([
        getSupplierEarnings(),
        getPayoutAccount(),
        getPayoutBalance(),
        getPayoutHistory(),
      ]);
      setEarnings(e);
      setAccount(a);
      setBalance(Number(b?.available_balance || 0));
      setHistory(h);
      if (a)
        setForm({
          holder_name: a.holder_name || "",
          bank_name: a.bank_name || "",
          account_number: "",
          ifsc: a.ifsc || "",
          upi_id: a.upi_id || "",
        });
    } catch (e) {
      setError(
        e?.response?.data?.message || "Unable to load earnings and payouts.",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const r = await savePayoutAccount(form);
      setMessage(r?.message || "Payout account saved.");
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to save payout account.");
    } finally {
      setSaving(false);
    }
  }
  async function request(e) {
    e.preventDefault();
    if (Number(payoutAmount) <= 0) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const r = await requestPayout(Number(payoutAmount));
      setMessage(r?.message || "Payout request submitted.");
      setPayoutAmount("");
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to request payout.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Earnings & payouts</h2>
          <p>
            Track supplier revenue, payout eligibility and payout processing
            state.
          </p>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 4 }, (_, i) => (
            <div className="skeleton" key={i} />
          ))}
        </div>
      ) : (
        <>
          <div className="metric-grid">
            <Metric label="Total sales" value={money(earnings?.total_sales)} />
            <Metric
              label="Delivered sales"
              value={money(earnings?.delivered_sales)}
            />
            <Metric
              label="Pending sales"
              value={money(earnings?.pending_sales)}
            />
            <Metric label="Available payout" value={money(balance)} />
          </div>
          <div className="two-panel-grid">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">Payout account</h3>
                  <p className="panel-subtitle">
                    Bank/UPI details are displayed only in masked or permitted
                    form.
                  </p>
                </div>
                {account && (
                  <span
                    className={`status-chip ${account.is_verified ? "success" : "warning"}`}
                  >
                    {account.is_verified ? "VERIFIED" : "AWAITING VERIFICATION"}
                  </span>
                )}
              </div>
              <form className="form-card" onSubmit={save}>
                <div className="form-grid-2">
                  <Field
                    label="Account holder"
                    name="holder_name"
                    value={form.holder_name}
                    set={setForm}
                    required
                  />
                  <Field
                    label="Bank name"
                    name="bank_name"
                    value={form.bank_name}
                    set={setForm}
                  />
                  <Field
                    label="Account number"
                    name="account_number"
                    value={form.account_number}
                    set={setForm}
                    placeholder={
                      account?.account_number
                        ? "Stored account ••••"
                        : "Enter account number"
                    }
                  />
                  <Field
                    label="IFSC"
                    name="ifsc"
                    value={form.ifsc}
                    set={setForm}
                  />
                  <Field
                    label="UPI ID"
                    name="upi_id"
                    value={form.upi_id}
                    set={setForm}
                  />
                </div>
                <button className="action-link" disabled={saving}>
                  Save payout details
                </button>
              </form>
            </section>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">Request a payout</h3>
                  <p className="panel-subtitle">
                    Only delivered supplier sales that are not already allocated
                    can be requested.
                  </p>
                </div>
                <FaWallet />
              </div>
              <form className="form-card" onSubmit={request}>
                <div className="payout-available">
                  <span>Available</span>
                  <strong>{money(balance)}</strong>
                </div>
                <label className="form-label">
                  Amount
                  <input
                    className="form-control"
                    type="number"
                    min="1"
                    max={balance}
                    step="0.01"
                    value={payoutAmount}
                    onChange={(e) => setPayoutAmount(e.target.value)}
                    disabled={!account?.is_verified || balance <= 0}
                  />
                </label>
                <button
                  className="action-link"
                  disabled={
                    saving ||
                    !account?.is_verified ||
                    balance <= 0 ||
                    Number(payoutAmount) <= 0
                  }
                >
                  {account?.is_verified
                    ? "Request payout"
                    : "Payout account must be verified"}
                </button>
                {!account?.is_verified && (
                  <p className="muted payout-note">
                    <FaExclamationTriangle /> Your payout account is awaiting
                    verification.
                  </p>
                )}
              </form>
            </section>
          </div>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Payout history</h3>
                <p className="panel-subtitle">
                  Transaction/reference details shared with your supplier
                  account.
                </p>
              </div>
            </div>
            {history.length ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Reference</th>
                      <th>Requested</th>
                      <th>Processed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((p) => (
                      <tr key={p.id}>
                        <td>
                          <b>{money(p.amount)}</b>
                        </td>
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
                            ? new Date(p.created_at).toLocaleString("en-IN")
                            : "—"}
                        </td>
                        <td>
                          {p.processed_at
                            ? new Date(p.processed_at).toLocaleString("en-IN")
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
                <h3>No payout requests</h3>
                <p>Your payout history will appear here.</p>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
function Metric({ label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">
        <FaWallet />
      </div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
function Field({ label, name, value, set, required, placeholder }) {
  return (
    <label className="form-label">
      {label}
      <input
        className="form-control"
        name={name}
        value={value}
        onChange={(e) => set((f) => ({ ...f, [name]: e.target.value }))}
        required={required}
        placeholder={placeholder}
      />
    </label>
  );
}
