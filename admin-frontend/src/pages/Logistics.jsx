import { useEffect, useState } from "react";
import {
  createLogisticsUser,
  getLogisticsUsers,
  updateLogisticsStatus,
} from "../services/logisticsService";
import PasswordInput from "../components/PasswordInput";

export default function Logistics() {
  const [search, setSearch] = useState("");
  const [users, setUsers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  async function load() {
    try {
      setLoading(true);
      setError("");
      setUsers(await getLogisticsUsers(search));
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to load logistics users.",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const id = setTimeout(load, 250);
    return () => clearTimeout(id);
  }, [search]);
  async function add(e) {
    e.preventDefault();
    try {
      await createLogisticsUser(form);
      setForm({ full_name: "", email: "", password: "" });
      setShow(false);
      await load();
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to create logistics user.",
      );
    }
  }
  async function status(id, next) {
    try {
      await updateLogisticsStatus(id, next);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to update access.");
    }
  }
  return (
    <div className="admin-page">
      <div className="admin-page-header admin-page-header-row">
        <div>
          <span className="admin-eyebrow">DELIVERY ACCESS</span>
          <h1>Logistics users</h1>
          <p>Manage authorized delivery operations accounts.</p>
        </div>
        <button
          className="admin-primary-btn"
          onClick={() => setShow((v) => !v)}
        >
          + Add logistics user
        </button>
      </div>
      {show && (
        <form className="admin-form-card" onSubmit={add}>
          <div className="admin-form-grid">
            <label>
              Full name
              <input
                value={form.full_name}
                onChange={(e) =>
                  setForm({ ...form, full_name: e.target.value })
                }
                required
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </label>
            <label>
              Password
              <PasswordInput
                id="admin-logistics-password"
                name="password"
                minLength={12}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="new-password"
                required
              />
            </label>
          </div>
          <button className="admin-primary-btn">Create user</button>
        </form>
      )}
      <div className="admin-toolbar">
        <div className="admin-search">
          <span>⌕</span>
          <input
            placeholder="Search logistics account"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      {error && <div className="admin-error">{error}</div>}
      <div className="admin-table-card">
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading…</div>
          ) : !users?.logistics_users?.length ? (
            <div className="admin-empty">No logistics users found.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {users.logistics_users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.full_name}</strong>
                      <span>#{u.id}</span>
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <select
                        className="admin-status-select"
                        value={u.status}
                        onChange={(e) => status(u.id, e.target.value)}
                      >
                        <option>ACTIVE</option>
                        <option>SUSPENDED</option>
                      </select>
                    </td>
                    <td>
                      {u.created_at
                        ? new Date(u.created_at).toLocaleDateString("en-IN")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
