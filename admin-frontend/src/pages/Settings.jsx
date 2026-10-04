import { useCallback, useEffect, useState } from "react";
import { getSettings, updateSetting } from "../services/contentService";

export default function Settings() {
  const [rows, setRows] = useState([]);
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const x = await getSettings();
      setRows(x);
      const d = {};
      x.forEach((r) => {
        d[r.key] = r.value;
      });
      setDraft(d);
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load settings.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    // The loader owns its loading/error state; this initial fetch is intentionally effect-driven.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);
  async function save(row) {
    try {
      setMessage("");
      await updateSetting(row.key, {
        value: draft[row.key],
        is_public: row.is_public,
        description: row.description,
      });
      setMessage(`${row.key} updated.`);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to update setting.");
    }
  }
  const label = (k) => k.replaceAll("_", " ");
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">PLATFORM CONFIGURATION</span>
        <h1>Settings</h1>
        <p>
          Business rules live in the backend database; customer-facing values
          can be marked public.
        </p>
      </div>
      {error && <div className="admin-error">{error}</div>}
      {message && <div className="admin-success">{message}</div>}
      {loading ? (
        <div className="admin-empty">Loading settings…</div>
      ) : (
        <div className="settings-grid">
          {rows.map((row) => (
            <section className="admin-detail-card" key={row.key}>
              <h2>{label(row.key)}</h2>
              <p>{row.description || "Platform setting"}</p>
              <label className="setting-field">
                Value
                <input
                  value={
                    typeof draft[row.key] === "object"
                      ? JSON.stringify(draft[row.key])
                      : (draft[row.key] ?? "")
                  }
                  onChange={(e) =>
                    setDraft({ ...draft, [row.key]: e.target.value })
                  }
                />
              </label>
              <div className="setting-meta">
                <span>
                  {row.is_public
                    ? "Public storefront setting"
                    : "Private business setting"}
                </span>
                <button className="admin-primary-btn" onClick={() => save(row)}>
                  Save
                </button>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
