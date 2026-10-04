import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { FiArrowRight, FiLock, FiMail, FiUser } from "react-icons/fi";
import { useAuth } from "../../context/AuthContext";
import { getApiMessage } from "../../utils/apiError";
import PasswordInput from "../../components/common/PasswordInput";

export default function Register() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { register } = useAuth();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      const redirect = searchParams.get("redirect");
      navigate(
        `/login${redirect ? `?redirect=${encodeURIComponent(redirect)}` : ""}`,
        { replace: true, state: { registered: true } },
      );
    } catch (err) {
      setError(getApiMessage(err, "Unable to create your account."));
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
        <span className="cc-eyebrow">Create customer account</span>
        <h1>Start shopping</h1>
        <p>Create one account for your cart, wishlist, addresses and orders.</p>

        {error ? (
          <div className="cc-form-error" role="alert">
            {error}
          </div>
        ) : null}

        <form onSubmit={submit} className="cc-form">
          <label>
            Full name
            <span className="cc-input-icon">
              <FiUser />
              <input
                type="text"
                autoComplete="name"
                required
                minLength={2}
                value={form.full_name}
                onChange={(e) =>
                  setForm({ ...form, full_name: e.target.value })
                }
              />
            </span>
          </label>
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
                id="customer-register-password"
                name="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </span>
          </label>
          <label>
            Confirm password
            <span className="cc-input-icon">
              <FiLock />
              <PasswordInput
                id="customer-register-confirm-password"
                name="confirm_password"
                autoComplete="new-password"
                required
                minLength={8}
                value={form.confirm_password}
                onChange={(e) =>
                  setForm({ ...form, confirm_password: e.target.value })
                }
              />
            </span>
          </label>
          <button
            className="cc-btn primary full"
            disabled={loading}
            type="submit"
          >
            {loading ? "Creating account…" : "Create account"}
            <FiArrowRight />
          </button>
        </form>

        <p className="cc-auth-foot">
          Already have an account?{" "}
          <Link
            to={`/login${searchParams.get("redirect") ? `?redirect=${encodeURIComponent(searchParams.get("redirect"))}` : ""}`}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
