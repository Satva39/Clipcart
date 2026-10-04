import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginAdmin } from "../services/authService";
import PasswordInput from "../components/PasswordInput";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      setLoading(true);
      await loginAdmin(email.trim().toLowerCase(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="admin-auth-page">
      <div className="admin-auth-card">
        <div className="admin-auth-brand">
          <div className="admin-auth-logo">Clipcart</div>
          <span>PRIVATE ADMIN PORTAL</span>
        </div>
        <div className="admin-auth-icon">🔐</div>
        <h1>Administrator sign in</h1>
        <p className="admin-auth-subtitle">
          Backend-authorized access to platform controls and aggregate
          operations.
        </p>
        {error && <div className="admin-auth-error">{error}</div>}
        <form className="admin-auth-form" onSubmit={submit}>
          <label htmlFor="admin-email">Admin email</label>
          <input
            id="admin-email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            type="email"
            required
          />
          <label htmlFor="admin-password">Password</label>
          <PasswordInput
            id="admin-password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button className="admin-login-btn" disabled={loading}>
            {loading ? "Signing in…" : "Sign in securely"}
          </button>
        </form>
        <Link className="admin-forgot-link" to="/forgot-password">
          Forgot admin password?
        </Link>
        <div className="admin-auth-security">
          Admin authorization is validated by the backend on every protected
          request. Customer order history and supplier catalog internals are not
          available here.
        </div>
      </div>
    </div>
  );
}
