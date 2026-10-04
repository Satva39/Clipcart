import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../../services/api";
import { getRegistrationStatus } from "../../services/supplierService";
import PasswordInput from "../../components/PasswordInput";
import "./auth.css";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/accounts/login", form);
      const result = data?.data;
      if (
        !result?.access_token ||
        String(result.user?.role).toUpperCase() !== "SUPPLIER"
      )
        throw new Error("This is not a supplier account.");
      localStorage.setItem(
        "clipcart_supplier_access_token",
        result.access_token,
      );
      localStorage.setItem(
        "clipcart_supplier_refresh_token",
        result.refresh_token || "",
      );
      localStorage.setItem(
        "clipcart_supplier_user",
        JSON.stringify(result.user),
      );
      let status = result.user?.status;
      try {
        const onboarding = await getRegistrationStatus();
        status = onboarding.account_status;
      } catch {
        /* status will be enforced by protected routes */
      }
      if (status === "PENDING") navigate("/register/payment");
      else if (status && status !== "ACTIVE") navigate("/account-status");
      else navigate("/");
    } catch (err) {
      setError(
        err?.response?.data?.message || err?.message || "Unable to login.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page-modern">
      <div className="auth-card-modern">
        <div className="auth-brand">
          CLIPCART <span>SUPPLIER</span>
        </div>
        <div className="auth-eyebrow">Supplier marketplace portal</div>
        <h1>Welcome back</h1>
        <p className="auth-subtitle">
          Sign in to manage products, orders, inventory and payouts.
        </p>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={submit}>
          <label>
            Email
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <PasswordInput
              id="supplier-login-password"
              name="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete="current-password"
              required
            />
          </label>
          <button disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-footer">
          New supplier? <Link to="/register">Create an account →</Link>
        </p>
      </div>
    </div>
  );
}
