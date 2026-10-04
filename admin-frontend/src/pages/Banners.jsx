import { useEffect, useRef, useState } from "react";
import {
  deactivateBanner,
  deleteBanner,
  getBanners,
  saveBanner,
  uploadBannerImage,
} from "../services/contentService";

const empty = {
  title: "",
  subtitle: "",
  image_url: "",
  cta_label: "",
  destination: "",
  placement: "HOME_HERO",
  is_active: true,
  starts_at: "",
  ends_at: "",
  sort_order: 0,
};

function toDatetimeLocalInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toServerDateTime(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function visibilityLabel(row) {
  if (!row?.is_active) return "INACTIVE";

  const now = Date.now();
  const start = row.starts_at ? new Date(row.starts_at).getTime() : null;
  const end = row.ends_at ? new Date(row.ends_at).getTime() : null;

  // Compute the schedule locally first so the UI stays truthful even if an
  // older backend response does not contain visibility_status.
  if (start && Number.isFinite(start) && start > now) return "SCHEDULED";
  if (end && Number.isFinite(end) && end < now) return "ENDED";
  if (row?.visibility_status) {
    return String(row.visibility_status).replaceAll("_", " ");
  }
  if (!row?.image_url) return "MISSING IMAGE";
  return "VISIBLE";
}

const placements = [
  { value: "HOME_HERO", label: "Homepage hero" },
  { value: "HOME_PROMO", label: "Homepage promotion strip" },
  { value: "HOME_CATEGORY", label: "Homepage category promotion" },
];

export default function Banners() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const fileRef = useRef(null);

  async function load() {
    try {
      setLoading(true);
      setError("");
      setRows(await getBanners());
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load banners.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function startCreate() {
    setEditing(null);
    setForm(empty);
    setImageFile(null);
    setImagePreview("");
    setError("");
    setShow(true);
  }

  function edit(row) {
    setEditing(row.id);
    setForm({
      ...empty,
      ...row,
      placement: row.placement || "HOME_HERO",
      starts_at: toDatetimeLocalInput(row.starts_at),
      ends_at: toDatetimeLocalInput(row.ends_at),
    });
    setImageFile(null);
    setImagePreview(row.image_url || "");
    setError("");
    setShow(true);
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!editing && !imageFile && !form.image_url) {
      setError("Please choose a banner image from your PC.");
      return;
    }

    try {
      setUploading(Boolean(imageFile));
      let imageUrl = form.image_url;
      if (imageFile) {
        const uploaded = await uploadBannerImage(imageFile);
        imageUrl = uploaded?.image_url || "";
        if (!imageUrl)
          throw new Error("The image upload returned no image URL.");
      }

      await saveBanner(
        {
          ...form,
          image_url: imageUrl,
          sort_order: Number(form.sort_order || 0),
          placement: form.placement || "HOME_HERO",
          destination: form.destination?.trim() || "",
          cta_label: form.cta_label?.trim() || "",
          starts_at: toServerDateTime(form.starts_at),
          ends_at: toServerDateTime(form.ends_at),
        },
        editing,
      );

      setShow(false);
      setEditing(null);
      setForm(empty);
      setImageFile(null);
      setImagePreview("");
      await load();
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to save banner.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function deactivate(id) {
    if (
      !window.confirm(
        "Deactivate this banner? It will stop showing on the customer website.",
      )
    )
      return;
    try {
      setError("");
      await deactivateBanner(id);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to deactivate banner.");
    }
  }

  async function removeBanner(row) {
    if (
      !window.confirm(
        `Delete "${row.title || "this banner"}" permanently? This cannot be undone.`,
      )
    ) {
      return;
    }

    try {
      setError("");
      await deleteBanner(row.id);
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to delete banner.");
    }
  }

  async function showNow(row) {
    if (
      !window.confirm(
        `Show "${row.title || "this banner"}" on the customer website now?`,
      )
    ) {
      return;
    }
    try {
      setError("");
      await saveBanner(
        {
          is_active: true,
          starts_at: null,
          ends_at: null,
        },
        row.id,
      );
      await load();
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to publish banner now.");
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header admin-page-header-row">
        <div>
          <span className="admin-eyebrow">CUSTOMER CONTENT</span>
          <h1>Hero & promotional banners</h1>
          <p>
            Upload images from your PC, choose a real customer-site placement,
            and control when each banner is visible. Only a banner marked
            VISIBLE is currently shown to customers.
          </p>
        </div>
        <button className="admin-primary-btn" onClick={startCreate}>
          + Add banner
        </button>
      </div>

      {show && (
        <form className="admin-form-card admin-banner-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="wide-field">
              Banner image
              <div className="admin-banner-upload-row">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  hidden
                  onChange={(event) => {
                    const file = event.target.files?.[0] || null;
                    setImageFile(file);
                    setImagePreview(
                      file ? URL.createObjectURL(file) : form.image_url || "",
                    );
                  }}
                />
                <button
                  type="button"
                  className="admin-secondary-btn"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                >
                  {imageFile ? "Choose another image" : "Choose image from PC"}
                </button>
                <span className="admin-upload-name">
                  {imageFile?.name ||
                    (form.image_url
                      ? "Current image selected"
                      : "No image selected")}
                </span>
              </div>
              {imagePreview ? (
                <img
                  className="admin-banner-preview"
                  src={imagePreview}
                  alt="Banner preview"
                />
              ) : null}
            </label>

            <label>
              Title
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </label>
            <label>
              Subtitle
              <input
                value={form.subtitle || ""}
                onChange={(e) => setForm({ ...form, subtitle: e.target.value })}
              />
            </label>
            <label>
              Banner placement
              <select
                value={form.placement}
                onChange={(e) =>
                  setForm({ ...form, placement: e.target.value })
                }
                required
              >
                {placements.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              CTA label <span className="admin-field-hint">optional</span>
              <input
                value={form.cta_label || ""}
                onChange={(e) =>
                  setForm({ ...form, cta_label: e.target.value })
                }
                placeholder="Shop now"
              />
            </label>
            <label>
              Destination <span className="admin-field-hint">optional</span>
              <input
                value={form.destination || ""}
                onChange={(e) =>
                  setForm({ ...form, destination: e.target.value })
                }
                placeholder="/products"
              />
            </label>
            <label>
              Start date/time
              <input
                type="datetime-local"
                value={form.starts_at || ""}
                onChange={(e) =>
                  setForm({ ...form, starts_at: e.target.value })
                }
              />
            </label>
            <label>
              End date/time
              <input
                type="datetime-local"
                value={form.ends_at || ""}
                onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
              />
            </label>
            <label>
              Sort order
              <input
                type="number"
                value={form.sort_order ?? 0}
                onChange={(e) =>
                  setForm({ ...form, sort_order: e.target.value })
                }
              />
            </label>
            <label>
              Visibility
              <select
                value={form.is_active ? "true" : "false"}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.value === "true" })
                }
              >
                <option value="true">Active — show on customer site</option>
                <option value="false">
                  Inactive — hide from customer site
                </option>
              </select>
            </label>
          </div>
          <p className="admin-banner-help">
            The destination is optional. With no destination, the uploaded
            banner is displayed as an image without a click target. Active
            banners without dates show immediately; scheduled banners appear
            only during their window. Inactive or expired banners are filtered
            out by the backend.
          </p>
          <div className="admin-form-actions">
            <button className="admin-primary-btn" disabled={uploading}>
              {uploading
                ? "Uploading…"
                : editing
                  ? "Save changes"
                  : "Create banner"}
            </button>
            <button
              type="button"
              className="admin-secondary-btn"
              onClick={() => {
                setShow(false);
                setImageFile(null);
                setImagePreview("");
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && <div className="admin-error">{error}</div>}

      <div className="admin-table-card">
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading banners…</div>
          ) : !rows.length ? (
            <div className="admin-empty">No banners configured.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Banner</th>
                  <th>Placement</th>
                  <th>CTA / destination</th>
                  <th>Schedule</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="admin-banner-cell">
                      {r.image_url ? (
                        <img
                          src={r.image_url}
                          alt=""
                          loading="lazy"
                          decoding="async"
                        />
                      ) : null}
                      <div>
                        <strong>{r.title}</strong>
                        <span>{r.subtitle || "No subtitle"}</span>
                      </div>
                    </td>
                    <td>
                      {placements.find((item) => item.value === r.placement)
                        ?.label ||
                        r.placement ||
                        "Homepage hero"}
                    </td>
                    <td>
                      {r.cta_label || "Image only"}
                      <span>{r.destination || "No destination"}</span>
                    </td>
                    <td>
                      {r.starts_at
                        ? new Date(r.starts_at).toLocaleString("en-IN")
                        : "Now"}
                      <span>
                        {r.ends_at
                          ? new Date(r.ends_at).toLocaleString("en-IN")
                          : "No end"}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`admin-status ${visibilityLabel(r).toLowerCase().replaceAll(" ", "-")}`}
                      >
                        {visibilityLabel(r)}
                      </span>
                    </td>
                    <td className="admin-banner-actions-cell">
                      <div className="admin-banner-actions">
                        <button
                          type="button"
                          className="admin-small-btn"
                          onClick={() => edit(r)}
                        >
                          Edit
                        </button>
                        {visibilityLabel(r) !== "VISIBLE" && r.image_url ? (
                          <button
                            type="button"
                            className="admin-small-btn banner-show-now-btn"
                            onClick={() => showNow(r)}
                          >
                            Show now
                          </button>
                        ) : null}
                        {r.is_active && (
                          <button
                            type="button"
                            className="admin-danger-btn"
                            onClick={() => deactivate(r.id)}
                          >
                            Deactivate
                          </button>
                        )}
                        <button
                          type="button"
                          className="admin-delete-btn"
                          onClick={() => removeBanner(r)}
                        >
                          Delete
                        </button>
                      </div>
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
