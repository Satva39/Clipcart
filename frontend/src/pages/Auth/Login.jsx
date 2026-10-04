import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { FiArrowRight, FiLock, FiMail } from "react-icons/fi";
import { useAuth } from "../../context/AuthContext";
import { getApiMessage } from "../../utils/apiError";
import PasswordInput from "../../components/common/PasswordInput";

function safeRedirect(value) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, isAuthenticated, loading: authLoading } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && isAuthenticated)
      navigate(safeRedirect(searchParams.get("redirect")), { replace: true });
  }, [authLoading, isAuthenticated, navigate, searchParams]);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(form.email.trim(), form.password);
      navigate(safeRedirect(searchParams.get("redirect")), { replace: true });
    } catch (err) {
      setError(
        getApiMessage(
          err,
          err?.message || "Unable to sign in. Check your credentials.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="cc-auth-page">
      <div className="cc-auth-card">
        <div className="cc-auth-brand">
          Clip<span>cart</span>
        </div>
        <span className="cc-eyebrow">Customer sign in</span>
        <h1>Welcome back</h1>
        <p>Sign in to keep your wishlist, cart and orders synced.</p>

        {error ? (
          <div className="cc-form-error" role="alert">
            {error}
          </div>
        ) : null}

        <form onSubmit={submit} className="cc-form">
          <label>
            Email address
            <span className="cc-input-icon">
              <FiMail />
              <input
                type="email"
                autoComplete="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </span>
          </label>
          <label>
            Password
            <span className="cc-input-icon">
              <FiLock />
              <PasswordInput
                id="customer-login-password"
                name="password"
                autoComplete="current-password"
                required
                minLength={6}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </span>
          </label>
          <button
            className="cc-btn primary full"
            disabled={loading}
            type="submit"
          >
            {loading ? "Signing in…" : "Sign in"}
            <FiArrowRight />
          </button>
        </form>

        <p className="cc-auth-foot">
          New to Clipcart?{" "}
          <Link
            to={`/register${searchParams.get("redirect") ? `?redirect=${encodeURIComponent(searchParams.get("redirect"))}` : ""}`}
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
