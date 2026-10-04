import { useEffect, useState } from "react";
import {
  getAdminProfile,
  changeAdminPassword,
} from "../services/profileService";
import PasswordInput from "../components/PasswordInput";

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    getAdminProfile()
      .then(setProfile)
      .catch((err) =>
        setError(err?.response?.data?.message || "Unable to load profile."),
      )
      .finally(() => setLoading(false));
  }, []);
  async function submit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (form.new_password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (form.new_password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    try {
      setSaving(true);
      await changeAdminPassword(
        form.current_password,
        form.new_password,
        form.confirm_password,
      );
      setForm({ current_password: "", new_password: "", confirm_password: "" });
      setMessage("Password changed successfully.");
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to change password.");
    } finally {
      setSaving(false);
    }
  }
  if (loading)
    return (
      <div className="admin-page">
        <div className="admin-empty">Loading profile…</div>
      </div>
    );
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">PRIVATE IDENTITY</span>
        <h1>Profile & security</h1>
        <p>Manage the configured administrator account.</p>
      </div>
      {error && <div className="admin-error">{error}</div>}
      {message && <div className="admin-success">{message}</div>}
      <div className="admin-detail-grid">
        <section className="admin-detail-card">
          <h2>Administrator</h2>
          <div className="admin-total-row">
            <span>Name</span>
            <strong>{profile?.name || "—"}</strong>
          </div>
          <div className="admin-total-row">
            <span>Email</span>
            <strong>{profile?.email || "—"}</strong>
          </div>
          <div className="admin-total-row">
            <span>Role</span>
            <strong>ADMIN</strong>
          </div>
          <p>
            The email identity is backend-configured and cannot be changed from
            this portal.
          </p>
        </section>
        <section className="admin-detail-card">
          <h2>Change password</h2>
          <form className="admin-auth-form" onSubmit={submit}>
            <label>Current password</label>
            <PasswordInput
              id="admin-current-password"
              name="current_password"
              autoComplete="current-password"
              value={form.current_password}
              onChange={(e) =>
                setForm({ ...form, current_password: e.target.value })
              }
              required
            />
            <label>New password</label>
            <PasswordInput
              id="admin-new-password"
              name="new_password"
              minLength={12}
              autoComplete="new-password"
              value={form.new_password}
              onChange={(e) =>
                setForm({ ...form, new_password: e.target.value })
              }
              required
            />
            <label>Confirm password</label>
            <PasswordInput
              id="admin-confirm-password"
              name="confirm_password"
              minLength={12}
              autoComplete="new-password"
              value={form.confirm_password}
              onChange={(e) =>
                setForm({ ...form, confirm_password: e.target.value })
              }
              required
            />
            <button className="admin-primary-btn" disabled={saving}>
              {saving ? "Updating…" : "Change password"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
