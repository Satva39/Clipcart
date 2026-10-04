import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaShieldAlt, FaTruck } from "react-icons/fa";

import { ACCESS_KEY, REFRESH_KEY, USER_KEY } from "../../services/api";
import { login } from "../../services/logisticsService";
import PasswordInput from "../../components/PasswordInput";
import "../../styles/auth.css";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const existingUser = localStorage.getItem(USER_KEY);
    const existingToken = localStorage.getItem(ACCESS_KEY);
    if (existingUser && existingToken) {
      try {
        const user = JSON.parse(existingUser);
        if (
          String(user.role).toUpperCase() === "LOGISTICS_MANAGER" &&
          String(user.status).toUpperCase() === "ACTIVE"
        ) {
          navigate("/", { replace: true });
        }
      } catch {
        // Ignore malformed stale session data.
      }
    }
  }, [navigate]);

  function handleChange(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await login(form.email.trim(), form.password);
      if (!data?.access_token || !data?.user) {
        throw new Error("The logistics session could not be created.");
      }

      localStorage.setItem(ACCESS_KEY, data.access_token);
      if (data.refresh_token) {
        localStorage.setItem(REFRESH_KEY, data.refresh_token);
      }
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));

      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.message || err?.message || "Unable to sign in.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="logistics-auth-shell">
      <section className="logistics-auth-card">
        <div className="logistics-auth-icon">
          <FaTruck />
        </div>

        <div className="logistics-auth-brand">CLIPCART LOGISTICS</div>
        <h1>Operations sign in</h1>
        <p className="logistics-auth-subtitle">
          Restricted access for authorized logistics managers and delivery
          operations.
        </p>

        <div className="logistics-security-note">
          <FaShieldAlt />
          <span>
            Backend authorization is enforced for every logistics endpoint.
          </span>
        </div>

        {error && <div className="logistics-auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="logistics-auth-form">
          <label htmlFor="email">Work email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            value={form.email}
            onChange={handleChange}
            placeholder="manager@clipcart.in"
            required
          />

          <label htmlFor="password">Password</label>
          <PasswordInput
            id="password"
            name="password"
            autoComplete="current-password"
            value={form.password}
            onChange={handleChange}
            placeholder="Enter password"
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in to logistics"}
          </button>
        </form>
      </section>
    </main>
  );
}
