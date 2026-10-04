import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerSupplier } from "../../services/supplierService";
import PasswordInput from "../../components/PasswordInput";
import "./auth.css";

const initial = {
  name: "",
  business_name: "",
  email: "",
  phone: "",
  password: "",
  confirmPassword: "",
  gst_number: "",
  holder_name: "",
  bank_name: "",
  account_number: "",
  ifsc: "",
  upi_id: "",
};

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword)
      return setError("Passwords do not match.");
    setLoading(true);
    try {
      const data = await registerSupplier(form);
      localStorage.setItem("clipcart_supplier_access_token", data.access_token);
      localStorage.setItem(
        "clipcart_supplier_refresh_token",
        data.refresh_token || "",
      );
      localStorage.setItem("clipcart_supplier_user", JSON.stringify(data.user));
      localStorage.setItem(
        "clipcart_supplier_registration",
        JSON.stringify({
          business_name: form.business_name,
          full_name: form.name,
          email: form.email,
          phone: form.phone,
        }),
      );
      navigate("/register/payment");
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          "Registration failed. Please review the details and try again.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="auth-page-modern">
      <div className="auth-card-modern auth-card-register">
        <div className="auth-brand">
          CLIPCART <span>SUPPLIER</span>
        </div>
        <div className="auth-eyebrow">Step 1 of 2 · Account setup</div>
        <h1>Become a supplier</h1>
        <p className="auth-subtitle">
          Create your supplier profile. The registration fee is verified
          separately by Razorpay.
        </p>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={submit} className="register-form">
          <div className="form-section">
            <h3>Account</h3>
            <div className="form-grid">
              <label>
                Full name
                <input
                  name="name"
                  value={form.name}
                  onChange={change}
                  required
                />
              </label>
              <label>
                Business name
                <input
                  name="business_name"
                  value={form.business_name}
                  onChange={change}
                  required
                />
              </label>
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={change}
                  required
                />
              </label>
              <label>
                Phone
                <input
                  name="phone"
                  value={form.phone}
                  onChange={change}
                  required
                />
              </label>
              <label>
                Password
                <PasswordInput
                  id="supplier-register-password"
                  name="password"
                  value={form.password}
                  onChange={change}
                  minLength={12}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label>
                Confirm password
                <PasswordInput
                  id="supplier-register-confirm-password"
                  name="confirmPassword"
                  value={form.confirmPassword}
                  onChange={change}
                  minLength={12}
                  autoComplete="new-password"
                  required
                />
              </label>
            </div>
          </div>
          <div className="form-section">
            <h3>Business information</h3>
            <div className="form-grid">
              <label>
                GST number{" "}
                <span className="optional">optional where applicable</span>
                <input
                  name="gst_number"
                  value={form.gst_number}
                  onChange={change}
                  placeholder="GSTIN"
                />
              </label>
            </div>
          </div>
          <div className="form-section">
            <h3>Payout information</h3>
            <p>
              Provide a UPI ID or bank details. Bank account numbers are stored
              server-side and masked when displayed.
            </p>
            <div className="form-grid">
              <label>
                Account holder
                <input
                  name="holder_name"
                  value={form.holder_name}
                  onChange={change}
                />
              </label>
              <label>
                UPI ID <span className="optional">or bank account below</span>
                <input
                  name="upi_id"
                  value={form.upi_id}
                  onChange={change}
                  placeholder="name@bank"
                />
              </label>
              <label>
                Bank name
                <input
                  name="bank_name"
                  value={form.bank_name}
                  onChange={change}
                />
              </label>
              <label>
                Account number
                <input
                  name="account_number"
                  value={form.account_number}
                  onChange={change}
                  inputMode="numeric"
                />
              </label>
              <label>
                IFSC
                <input name="ifsc" value={form.ifsc} onChange={change} />
              </label>
            </div>
          </div>
          <div className="fee-box-modern">
            <strong>Configured fee</strong>
            <div>
              <b>One-time supplier registration fee</b>
              <span>
                Paid through Razorpay and activated only after server-side
                verification.
              </span>
            </div>
          </div>
          <button disabled={loading}>
            {loading ? "Creating supplier account…" : "Continue to payment"}
          </button>
        </form>
        <p className="auth-footer">
          Already registered? <Link to="/login">Supplier login →</Link>
        </p>
      </div>
    </div>
  );
}
