import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotAdminPassword } from "../services/authService";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      setLoading(true);
      const result = await forgotAdminPassword(email.trim().toLowerCase());
      setMessage(
        result.message ||
          "If the email is authorized, reset instructions have been sent.",
      );
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to process the request.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="admin-auth-page">
      <div className="admin-auth-card">
        <div className="admin-auth-brand">
          <div className="admin-auth-logo">Clipcart</div>
          <span>ADMIN RECOVERY</span>
        </div>
        <h1>Forgot password</h1>
        <p className="admin-auth-subtitle">
          Use the configured private administrator email.
        </p>
        {error && <div className="admin-auth-error">{error}</div>}
        {message && <div className="admin-auth-security">{message}</div>}
        <form className="admin-auth-form" onSubmit={submit}>
          <label>Admin email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
          <button className="admin-login-btn" disabled={loading}>
            {loading ? "Sending…" : "Send reset email"}
          </button>
        </form>
        <Link to="/login" className="admin-forgot-link">
          ← Back to login
        </Link>
      </div>
    </div>
  );
}
