import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetAdminPassword } from "../services/authService";
import PasswordInput from "../components/PasswordInput";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    try {
      setLoading(true);
      const result = await resetAdminPassword(token, password, confirm);
      setMessage(result.message || "Password reset successfully.");
      setTimeout(() => navigate("/login", { replace: true }), 1200);
    } catch (err) {
      setError(
        err?.response?.data?.message || "Reset link is invalid or expired.",
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
        <h1>Reset password</h1>
        <p className="admin-auth-subtitle">
          Choose a new administrator password.
        </p>
        {error && <div className="admin-auth-error">{error}</div>}
        {message && <div className="admin-auth-security">{message}</div>}
        <form className="admin-auth-form" onSubmit={submit}>
          <label>New password</label>
          <PasswordInput
            id="admin-reset-password"
            name="password"
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
          <label>Confirm password</label>
          <PasswordInput
            id="admin-reset-confirm-password"
            name="confirm_password"
            minLength={12}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
          />
          <button className="admin-login-btn" disabled={!token || loading}>
            {loading ? "Updating…" : "Reset password"}
          </button>
        </form>
        <Link to="/login" className="admin-forgot-link">
          ← Back to login
        </Link>
      </div>
    </div>
  );
}
