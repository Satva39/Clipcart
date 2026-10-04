import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  FaArrowLeft,
  FaCheckCircle,
  FaClipboardCheck,
  FaMapMarkerAlt,
  FaPhoneAlt,
  FaRedoAlt,
  FaTruck,
} from "react-icons/fa";

import {
  assignReturnPickup,
  getReturn,
  markReturnDeliveredToSupplier,
  markReturnPickedUp,
} from "../../services/logisticsService";
import "./returnDetail.css";

const ACTIONS = {
  ASSIGN: "assign",
  PICKUP: "pickup",
  DELIVER: "deliver",
};

function getStatus(value) {
  return String(value || "REQUESTED").toUpperCase();
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";
}

function errorMessage(error, fallback) {
  const value = error?.response?.data?.message;
  return typeof value === "string" && value.trim() ? value : fallback;
}

const STEPS = [
  ["REQUESTED", "Return requested"],
  ["PICKUP_ASSIGNED", "Pickup assigned"],
  ["PICKED_UP", "Picked up from customer"],
  ["IN_TRANSIT_TO_SUPPLIER", "In transit to supplier"],
  ["RECEIVED", "Delivered to supplier"],
];

function stepIndex(status) {
  if (status === "PICKUP_ASSIGNED") return 1;
  if (status === "PICKED_UP") return 2;
  if (status === "IN_TRANSIT_TO_SUPPLIER") return 3;
  if (status === "RECEIVED") return 4;
  return 0;
}

export default function ReturnDetail() {
  const { returnId } = useParams();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [agentName, setAgentName] = useState("");
  const [agentPhone, setAgentPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [completionPhoto, setCompletionPhoto] = useState(null);

  async function load() {
    try {
      setLoading(true);
      setError("");
      const data = await getReturn(returnId);
      setItem(data);
      setAgentName(data?.agent?.name || "");
      setAgentPhone(data?.agent?.phone || "");
      setNotes(data?.logistics_notes || "");
    } catch (err) {
      setError(errorMessage(err, "Unable to load this return request."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [returnId]);

  const completionPhotoPreview = useMemo(
    () => (completionPhoto ? URL.createObjectURL(completionPhoto) : ""),
    [completionPhoto],
  );

  useEffect(() => {
    return () => {
      if (completionPhotoPreview) {
        URL.revokeObjectURL(completionPhotoPreview);
      }
    };
  }, [completionPhotoPreview]);

  const status = getStatus(item?.status);
  const activeStep = useMemo(() => stepIndex(status), [status]);
  const isComplete = status === "RECEIVED";

  async function runAction(action, callback, message) {
    try {
      setSaving(action);
      setError("");
      setSuccess("");
      const result = await callback();
      setItem(result);
      if (action === ACTIONS.DELIVER) {
        setCompletionPhoto(null);
      }
      setSuccess(message);
      window.setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(errorMessage(err, "The return action could not be completed."));
    } finally {
      setSaving("");
    }
  }

  function submitAssignment(event) {
    event.preventDefault();
    if (!agentName.trim() || !agentPhone.trim()) {
      setError("Agent name and phone are required.");
      return;
    }
    runAction(
      ACTIONS.ASSIGN,
      () =>
        assignReturnPickup(
          returnId,
          agentName.trim(),
          agentPhone.trim(),
          notes.trim(),
        ),
      "Pickup agent assigned successfully.",
    );
  }

  function handlePickup() {
    if (
      !window.confirm(
        `Confirm that return #${returnId} was picked up from the customer?`,
      )
    )
      return;
    runAction(
      ACTIONS.PICKUP,
      () => markReturnPickedUp(returnId, notes.trim()),
      "Return picked up. It is now in transit to the supplier.",
    );
  }

  function handleSupplierDelivery() {
    if (!completionPhoto) {
      setError(
        "A photo of the returned product is required before completion.",
      );
      return;
    }
    if (
      !window.confirm(
        `Confirm that return #${returnId} has been delivered to the supplier?`,
      )
    )
      return;
    runAction(
      ACTIONS.DELIVER,
      () =>
        markReturnDeliveredToSupplier(returnId, notes.trim(), completionPhoto),
      "Return delivered to the supplier successfully.",
    );
  }

  if (loading)
    return (
      <div className="return-loading">Loading reverse-logistics record…</div>
    );

  if (!item) {
    return (
      <section className="return-page">
        <Link to="/queue" className="return-back">
          <FaArrowLeft /> Back to queue
        </Link>
        <div className="return-error">
          {error || "Return request not found."}
        </div>
      </section>
    );
  }

  const customer = item.customer || {};
  const address = customer.address || {};
  const supplier = item.supplier || {};
  const product = item.item || {};

  return (
    <section className="return-page">
      <div className="return-top">
        <div>
          <Link to="/queue" className="return-back">
            <FaArrowLeft /> Back to queue
          </Link>
          <div className="return-kicker">REVERSE LOGISTICS</div>
          <div className="return-title-row">
            <div>
              <h1>Return #{item.id}</h1>
              <p>
                Order #{item.order_id} · Requested {formatDate(item.created_at)}
              </p>
            </div>
            <span className={`return-status ${status.toLowerCase()}`}>
              {status === "RECEIVED"
                ? "DELIVERED TO SUPPLIER"
                : status.replaceAll("_", " ")}
            </span>
          </div>
        </div>
        <button
          type="button"
          className="return-refresh"
          onClick={load}
          disabled={saving !== ""}
        >
          <FaRedoAlt /> Refresh
        </button>
      </div>

      {error && <div className="return-alert return-alert-error">{error}</div>}
      {success && (
        <div className="return-alert return-alert-success">
          <FaCheckCircle /> {success}
        </div>
      )}

      <div className="return-grid">
        <main className="return-main">
          <section className="return-card">
            <div className="return-card-head">
              <div>
                <h2>Return item</h2>
                <p>
                  The exact item being moved back through reverse logistics.
                </p>
              </div>
            </div>
            <div className="return-item">
              <div className="return-item-icon">
                <FaTruck />
              </div>
              {product.image_url ? (
                <img
                  className="return-item-image"
                  src={product.image_url}
                  alt={product.product_name || "Returned product"}
                  loading="lazy"
                  decoding="async"
                />
              ) : null}
              <div>
                <strong>{product.product_name || "Product"}</strong>
                <span>
                  {product.variant
                    ? `Variant: ${product.variant}`
                    : "Standard item"}
                </span>
                <span>
                  Qty {product.quantity || 0} · SKU {product.sku || "—"}
                </span>
              </div>
            </div>
            <div className="return-reason">
              <span>Customer reason</span>
              <p>{item.reason}</p>
            </div>
          </section>

          <section className="return-card">
            <div className="return-card-head">
              <div>
                <h2>Pickup from customer</h2>
                <p>
                  Collect the returned item from the original delivery address.
                </p>
              </div>
              <FaMapMarkerAlt />
            </div>
            <div className="return-destination-grid">
              <div>
                <span>Customer</span>
                <strong>{customer.name || "—"}</strong>
                {customer.phone && (
                  <a href={`tel:${customer.phone}`}>
                    <FaPhoneAlt /> {customer.phone}
                  </a>
                )}
              </div>
              <div>
                <span>Address</span>
                <strong>{address.address_line_1 || "—"}</strong>
                <small>
                  {address.address_line_2 ? `${address.address_line_2}, ` : ""}
                  {address.landmark ? `${address.landmark}, ` : ""}
                  {address.city || ""}
                  {address.state ? `, ${address.state}` : ""}{" "}
                  {address.postal_code || ""}
                </small>
              </div>
            </div>
          </section>

          <section className="return-card">
            <div className="return-card-head">
              <div>
                <h2>Supplier destination</h2>
                <p>
                  After customer pickup, take the item back to the supplier.
                </p>
              </div>
              <FaTruck />
            </div>
            <div className="return-destination-grid">
              <div>
                <span>Supplier</span>
                <strong>
                  {supplier.business_name || supplier.name || "—"}
                </strong>
                {supplier.phone && (
                  <a href={`tel:${supplier.phone}`}>
                    <FaPhoneAlt /> {supplier.phone}
                  </a>
                )}
              </div>
              <div>
                <span>Return address</span>
                <strong>
                  {supplier.return_address ||
                    "Supplier return address not configured"}
                </strong>
                <small>
                  Use the supplier's configured receiving location when
                  available.
                </small>
              </div>
            </div>
          </section>

          <section className="return-card">
            <div className="return-card-head">
              <div>
                <h2>Return journey</h2>
                <p>
                  Every stage is recorded on the backend as the item moves home.
                </p>
              </div>
            </div>
            <div className="return-journey">
              {STEPS.map(([step, label], index) => {
                const complete =
                  index < activeStep || (isComplete && index === activeStep);
                const current = index === activeStep && !isComplete;
                return (
                  <div
                    className={`return-step ${complete ? "complete" : ""} ${current ? "current" : ""}`}
                    key={step}
                  >
                    <div className="return-step-number">
                      {complete ? <FaCheckCircle /> : index + 1}
                    </div>
                    <strong>{label}</strong>
                  </div>
                );
              })}
            </div>
          </section>
        </main>

        <aside className="return-side">
          <section className="return-card return-action-card">
            <div className="return-card-head">
              <div>
                <h2>Next action</h2>
                <p>
                  Only the valid action for the current return stage is enabled.
                </p>
              </div>
            </div>

            {LOGISTICS_ASSIGNABLE_STATUSES.includes(status) && (
              <form className="return-form" onSubmit={submitAssignment}>
                <label>
                  Agent name
                  <input
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    disabled={saving !== ""}
                  />
                </label>
                <label>
                  Agent phone
                  <input
                    value={agentPhone}
                    onChange={(e) => setAgentPhone(e.target.value)}
                    disabled={saving !== ""}
                  />
                </label>
                <label>
                  Notes
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Optional reverse-logistics notes"
                    disabled={saving !== ""}
                  />
                </label>
                <button
                  type="submit"
                  className="primary"
                  disabled={saving !== ""}
                >
                  <FaClipboardCheck />{" "}
                  {saving === ACTIONS.ASSIGN
                    ? "Saving…"
                    : "Assign pickup agent"}
                </button>
              </form>
            )}

            {status === "PICKUP_ASSIGNED" && (
              <div className="return-action-stack">
                <div className="return-agent-summary">
                  <span>Assigned agent</span>
                  <strong>{item.agent?.name}</strong>
                  <small>{item.agent?.phone}</small>
                </div>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional pickup notes"
                  disabled={saving !== ""}
                />
                <button
                  type="button"
                  className="primary"
                  onClick={handlePickup}
                  disabled={saving !== ""}
                >
                  <FaClipboardCheck />{" "}
                  {saving === ACTIONS.PICKUP
                    ? "Saving…"
                    : "Mark picked up from customer"}
                </button>
              </div>
            )}

            {status === "IN_TRANSIT_TO_SUPPLIER" && (
              <div className="return-action-stack">
                <div className="return-live-state">
                  The item has been picked up and is travelling to the supplier.
                </div>
                <label
                  className="return-upload-label"
                  htmlFor="completionPhoto"
                >
                  Completion photo <strong>*</strong>
                </label>
                <input
                  id="completionPhoto"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  capture="environment"
                  onChange={(event) =>
                    setCompletionPhoto(event.target.files?.[0] || null)
                  }
                  disabled={saving !== ""}
                  required
                />
                {completionPhotoPreview && (
                  <div className="return-completion-preview">
                    <img
                      src={completionPhotoPreview}
                      alt="Selected return completion photo"
                    />
                    <span>{completionPhoto?.name}</span>
                  </div>
                )}
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional delivery notes"
                  disabled={saving !== ""}
                />
                <button
                  type="button"
                  className="primary"
                  onClick={handleSupplierDelivery}
                  disabled={saving !== "" || !completionPhoto}
                >
                  <FaTruck />{" "}
                  {saving === ACTIONS.DELIVER
                    ? "Saving…"
                    : "Mark delivered to supplier"}
                </button>
              </div>
            )}

            {isComplete && (
              <div className="return-complete">
                <FaCheckCircle />
                <strong>Reverse logistics completed</strong>
                <span>
                  Delivered to supplier on{" "}
                  {formatDate(item.supplier_delivery?.time)}.
                </span>
                {item.completion_image_url && (
                  <a
                    className="return-completion-image-link"
                    href={item.completion_image_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img
                      src={item.completion_image_url}
                      alt={`Completion proof for return #${item.id}`}
                    />
                  </a>
                )}
              </div>
            )}
          </section>

          <section className="return-card return-meta-card">
            <div>
              <span>Customer pickup</span>
              <strong>{formatDate(item.pickup?.time)}</strong>
            </div>
            <div>
              <span>Supplier receipt</span>
              <strong>{formatDate(item.supplier_delivery?.time)}</strong>
            </div>
            <div>
              <span>Last update</span>
              <strong>{formatDate(item.updated_at)}</strong>
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}

const LOGISTICS_ASSIGNABLE_STATUSES = ["REQUESTED", "APPROVED"];
