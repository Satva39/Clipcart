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
  assignAgent,
  getOrder,
  markDelivered,
  markFailed,
  markOutForDelivery,
  markPickedUp,
  recordAttempt,
  retryFailed,
} from "../../services/logisticsService";
import "./orderDetail.css";

const ACTIONS = {
  ASSIGNED: "assigned",
  PICKED_UP: "picked",
  OFD: "ofd",
  ATTEMPT: "attempt",
  DELIVER: "deliver",
  FAIL: "fail",
  RETRY: "retry",
};

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";
}

function normalize(value) {
  return String(value || "").toUpperCase();
}

function getApiErrorMessage(error, fallback) {
  const message = error?.response?.data?.message;
  if (typeof message === "string" && message.trim()) {
    return message;
  }

  const errors = error?.response?.data?.errors;
  if (typeof errors === "string" && errors.trim()) {
    return errors;
  }
  if (errors && typeof errors === "object") {
    const entries = Object.entries(errors).flatMap(([field, value]) => {
      const values = Array.isArray(value) ? value : [value];
      return values
        .filter((item) => typeof item === "string" && item.trim())
        .map((item) => `${field}: ${item}`);
    });
    if (entries.length) return entries.join("; ");
  }

  return fallback;
}

function stageTone(stage) {
  return (
    {
      AWAITING_PICKUP: "amber",
      PICKUP_ASSIGNED: "blue",
      IN_TRANSIT: "blue",
      OUT_FOR_DELIVERY: "violet",
      FAILED: "red",
      DELIVERED: "green",
    }[stage] || "slate"
  );
}

export default function OrderDetail() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingAction, setSavingAction] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [agentName, setAgentName] = useState("");
  const [agentPhone, setAgentPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [customerNotes, setCustomerNotes] = useState("");
  const [pod, setPod] = useState("");
  const [attemptReason, setAttemptReason] = useState("");
  const [failureReason, setFailureReason] = useState("");
  const [nextAction, setNextAction] = useState("Reschedule delivery");
  const [modal, setModal] = useState("");
  const [deliveryPhoto, setDeliveryPhoto] = useState(null);
  const [deliveryPhotoPreview, setDeliveryPhotoPreview] = useState("");

  useEffect(() => {
    if (!deliveryPhoto) {
      setDeliveryPhotoPreview("");
      return undefined;
    }

    const url = URL.createObjectURL(deliveryPhoto);
    setDeliveryPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [deliveryPhoto]);

  async function loadOrder() {
    try {
      setLoading(true);
      setError("");
      const data = await getOrder(orderId);
      setOrder(data);
      setAgentName(data?.agent?.name || "");
      setAgentPhone(data?.agent?.phone || "");
      setNotes(data?.notes || "");
      setCustomerNotes(data?.customer_delivery_notes || "");
      setPod(data?.proof_of_delivery_reference || "");
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load this delivery record."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Order identity changes require a fresh backend record.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadOrder();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  const deliveryStatus = normalize(order?.delivery?.status);
  const pickupStatus = normalize(order?.pickup?.status);

  const actionLabel = useMemo(() => {
    if (deliveryStatus === "FAILED") return "Failed delivery — action required";
    if (deliveryStatus === "DELIVERED") return "Delivery completed";
    if (deliveryStatus === "OUT_FOR_DELIVERY") return "Out for delivery";
    if (deliveryStatus === "IN_TRANSIT") return "In transit";
    if (pickupStatus === "ASSIGNED") return "Pickup assigned";
    return "Awaiting pickup";
  }, [deliveryStatus, pickupStatus]);

  async function runAction(action, callback) {
    try {
      setSavingAction(action);
      setError("");
      setSuccess("");
      const result = await callback();
      setOrder(result);
      setSuccess("Delivery record updated successfully.");
      setModal("");
      setDeliveryPhoto(null);
      window.setTimeout(() => setSuccess(""), 2600);
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "The requested delivery action could not be completed.",
        ),
      );
    } finally {
      setSavingAction("");
    }
  }

  async function saveAssignment(event) {
    event.preventDefault();
    if (!agentName.trim() || !agentPhone.trim()) {
      setError("Agent name and phone are required.");
      return;
    }

    await runAction(ACTIONS.ASSIGNED, () =>
      assignAgent(orderId, agentName.trim(), agentPhone.trim()),
    );
  }

  function confirmAction(message) {
    return window.confirm(message);
  }

  function handlePickup() {
    if (
      !confirmAction(
        `Confirm pickup for order #${orderId}? This moves the order to shipped/in transit.`,
      )
    ) {
      return;
    }
    runAction(ACTIONS.PICKED_UP, () => markPickedUp(orderId));
  }

  function handleOFD() {
    if (
      !confirmAction(
        `Confirm order #${orderId} is out for delivery with ${order?.agent?.name || "the assigned agent"}?`,
      )
    ) {
      return;
    }
    runAction(ACTIONS.OFD, () => markOutForDelivery(orderId));
  }

  function submitAttempt(event) {
    event.preventDefault();
    if (!attemptReason.trim()) {
      setError("Enter a reason for the delivery attempt.");
      return;
    }
    runAction(ACTIONS.ATTEMPT, () =>
      recordAttempt(orderId, attemptReason.trim(), notes.trim()),
    );
  }

  function submitDelivered(event) {
    event.preventDefault();
    if (!deliveryPhoto) {
      setError(
        "A photo of the delivered product is required before completion.",
      );
      return;
    }
    if (
      !confirmAction(
        `Confirm order #${orderId} was delivered to the recipient?`,
      )
    ) {
      return;
    }
    runAction(ACTIONS.DELIVER, () =>
      markDelivered(orderId, {
        notes: notes.trim(),
        customer_delivery_notes: customerNotes.trim(),
        proof_of_delivery_reference: pod.trim(),
        completion_photo: deliveryPhoto,
      }),
    );
  }

  function submitFailed(event) {
    event.preventDefault();
    if (!failureReason.trim() || !nextAction.trim()) {
      setError("Failure reason and next action are required.");
      return;
    }
    if (
      !confirmAction(`Record a failed delivery attempt for order #${orderId}?`)
    ) {
      return;
    }
    runAction(ACTIONS.FAIL, () =>
      markFailed(
        orderId,
        failureReason.trim(),
        nextAction.trim(),
        notes.trim(),
      ),
    );
  }

  function handleRetry() {
    if (
      !confirmAction(`Start another delivery attempt for order #${orderId}?`)
    ) {
      return;
    }
    runAction(ACTIONS.RETRY, () => retryFailed(orderId, notes.trim()));
  }

  if (loading) {
    return <div className="order-loading">Loading delivery record…</div>;
  }

  if (!order) {
    return (
      <section className="order-page">
        <div className="order-error">
          {error || "Delivery record not found."}
        </div>
      </section>
    );
  }

  return (
    <section className="order-page">
      <div className="order-top">
        <div>
          <Link to="/queue" className="order-back">
            <FaArrowLeft /> Back to queue
          </Link>
          <div className="order-kicker">DELIVERY RECORD</div>
          <div className="order-title-row">
            <h1>Order #{order.order_id}</h1>
            <span className={`order-stage ${stageTone(order.stage)}`}>
              {actionLabel}
            </span>
          </div>
          <p>Placed {formatDate(order.created_order_at)}</p>
        </div>

        <button type="button" className="order-refresh" onClick={loadOrder}>
          <FaRedoAlt /> Refresh
        </button>
      </div>

      {error && <div className="order-error">{error}</div>}
      {success && (
        <div className="order-success">
          <FaCheckCircle /> {success}
        </div>
      )}

      <div className="order-layout">
        <div className="order-main-column">
          <section className="order-card">
            <div className="order-card-head">
              <div>
                <h2>Delivery destination</h2>
                <p>
                  Only the address and contact details required for delivery.
                </p>
              </div>
              <FaMapMarkerAlt />
            </div>

            <div className="destination-grid">
              <div>
                <span>Recipient</span>
                <strong>{order.customer?.name || "—"}</strong>
              </div>
              <div>
                <span>Phone</span>
                <strong>{order.customer?.phone || "—"}</strong>
                {order.customer?.phone && (
                  <a href={`tel:${order.customer.phone}`}>
                    <FaPhoneAlt /> Call
                  </a>
                )}
              </div>
              <div className="destination-full">
                <span>Address</span>
                <strong>
                  {order.destination?.address_line_1 || "—"}
                  {order.destination?.address_line_2
                    ? `, ${order.destination.address_line_2}`
                    : ""}
                </strong>
                <small>
                  {order.destination?.landmark
                    ? `${order.destination.landmark}, `
                    : ""}
                  {order.destination?.city}, {order.destination?.state}{" "}
                  {order.destination?.postal_code}
                </small>
              </div>
            </div>
          </section>

          <section className="order-card">
            <div className="order-card-head">
              <div>
                <h2>Pickup & assignment</h2>
                <p>Assign the delivery agent and record the pickup handoff.</p>
              </div>
              <FaTruck />
            </div>

            <div className="status-strip">
              <div>
                <span>Pickup status</span>
                <strong>{order.pickup?.status || "—"}</strong>
              </div>
              <div>
                <span>Pickup time</span>
                <strong>{formatDate(order.pickup?.time)}</strong>
              </div>
              <div>
                <span>Delivery status</span>
                <strong>{order.delivery?.status || "—"}</strong>
              </div>
            </div>

            <form className="agent-form" onSubmit={saveAssignment}>
              <div>
                <label htmlFor="agentName">Agent name</label>
                <input
                  id="agentName"
                  value={agentName}
                  onChange={(event) => setAgentName(event.target.value)}
                  disabled={
                    savingAction === ACTIONS.ASSIGNED ||
                    pickupStatus === "PICKED_UP"
                  }
                />
              </div>
              <div>
                <label htmlFor="agentPhone">Agent phone</label>
                <input
                  id="agentPhone"
                  value={agentPhone}
                  onChange={(event) => setAgentPhone(event.target.value)}
                  disabled={
                    savingAction === ACTIONS.ASSIGNED ||
                    pickupStatus === "PICKED_UP"
                  }
                />
              </div>
              <button
                type="submit"
                disabled={
                  savingAction !== "" ||
                  pickupStatus === "PICKED_UP" ||
                  normalize(order.order_status) !== "PROCESSING"
                }
              >
                {pickupStatus === "ASSIGNED"
                  ? "Save assignment"
                  : "Assign agent"}
              </button>
            </form>

            <div className="action-row">
              <button
                type="button"
                onClick={handlePickup}
                disabled={savingAction !== "" || pickupStatus !== "ASSIGNED"}
              >
                <FaClipboardCheck /> Mark picked up
              </button>
            </div>
          </section>

          <section className="order-card">
            <div className="order-card-head">
              <div>
                <h2>Order contents</h2>
                <p>Operational item reference for the pickup handoff.</p>
              </div>
            </div>
            <div className="item-list">
              {(order.items || []).map((item) => (
                <div className="item-row" key={item.id}>
                  <div>
                    <strong>{item.product_name}</strong>
                    <span>
                      {item.variant ? `${item.variant} · ` : ""}
                      SKU {item.sku || "—"}
                    </span>
                  </div>
                  <strong>× {item.quantity}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="order-card">
            <div className="order-card-head">
              <div>
                <h2>Shiprocket shipments</h2>
                <p>External courier state synchronized from Shiprocket.</p>
              </div>
              <FaTruck />
            </div>
            {Array.isArray(order.shipments) && order.shipments.length ? (
              <div className="item-list">
                {order.shipments.map((shipment) => (
                  <div className="item-row" key={shipment.id}>
                    <div>
                      <strong>
                        {shipment.supplier?.business_name ||
                          shipment.supplier?.name ||
                          "Supplier"}
                      </strong>
                      <span>
                        {String(shipment.status || "PENDING").replaceAll(
                          "_",
                          " ",
                        )}
                        {shipment.courier_name
                          ? ` · ${shipment.courier_name}`
                          : ""}
                      </span>
                      <span>
                        AWB {shipment.awb_code || "Awaiting assignment"}
                      </span>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <strong>{formatDate(shipment.last_synced_at)}</strong>
                      <span>
                        Pickup {formatDate(shipment.pickup_scheduled_at)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="pending-action-note">
                <span>Shiprocket</span>
                <strong>Shipment provisioning is pending.</strong>
              </div>
            )}
            {order.shipments?.some((shipment) => shipment.failure) ? (
              <div className="failure-box">
                {order.shipments
                  .filter((shipment) => shipment.failure)
                  .map((shipment) => (
                    <div key={`failure-${shipment.id}`}>
                      <span>Shipment failure</span>
                      <strong>
                        {shipment.failure.message || shipment.failure.code}
                      </strong>
                    </div>
                  ))}
              </div>
            ) : null}
          </section>

          <section className="order-card">
            <div className="order-card-head">
              <div>
                <h2>Delivery timeline</h2>
                <p>Operational and customer-visible order events.</p>
              </div>
            </div>
            <div className="timeline">
              {(order.timeline || []).map((event) => (
                <div className="timeline-item" key={event.id}>
                  <div className="timeline-marker" />
                  <div>
                    <strong>{event.title}</strong>
                    <span>{event.message}</span>
                    <small>{formatDate(event.occurred_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="order-side-column">
          <section className="order-card order-actions">
            <div className="order-card-head">
              <div>
                <h2>Next action</h2>
                <p>
                  Only actions permitted by the current server state are
                  enabled.
                </p>
              </div>
            </div>

            {deliveryStatus === "IN_TRANSIT" && (
              <button
                type="button"
                className="primary"
                disabled={savingAction !== ""}
                onClick={handleOFD}
              >
                Mark out for delivery
              </button>
            )}

            {deliveryStatus === "OUT_FOR_DELIVERY" && (
              <>
                <button
                  type="button"
                  className="primary"
                  disabled={savingAction !== ""}
                  onClick={() => setModal("deliver")}
                >
                  Mark delivered
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={savingAction !== ""}
                  onClick={() => setModal("attempt")}
                >
                  Record delivery attempt
                </button>
                <button
                  type="button"
                  className="danger"
                  disabled={savingAction !== ""}
                  onClick={() => setModal("fail")}
                >
                  Record failed delivery
                </button>
              </>
            )}

            {deliveryStatus === "FAILED" && (
              <button
                type="button"
                className="primary"
                disabled={savingAction !== ""}
                onClick={handleRetry}
              >
                Retry delivery
              </button>
            )}

            {deliveryStatus === "DELIVERED" && (
              <div className="completed-state">
                <FaCheckCircle />
                <strong>Delivered</strong>
                <span>{formatDate(order.delivery?.time)}</span>
                {order.delivery?.proof_of_delivery_image_url && (
                  <a
                    className="completion-image-link"
                    href={order.delivery.proof_of_delivery_image_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img
                      src={order.delivery.proof_of_delivery_image_url}
                      alt={`Delivery proof for order #${order.order_id}`}
                    />
                  </a>
                )}
              </div>
            )}

            {order.pending_action && (
              <div className="pending-action-note">
                <span>Pending action</span>
                <strong>{order.pending_action}</strong>
              </div>
            )}

            {order.delivery?.attempts > 0 && (
              <div className="attempt-count">
                <span>Delivery attempts</span>
                <strong>{order.delivery.attempts}</strong>
              </div>
            )}
          </section>

          <section className="order-card notes-card">
            <div className="order-card-head">
              <div>
                <h2>Operational notes</h2>
                <p>Saved to the delivery record.</p>
              </div>
            </div>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Internal delivery notes"
              rows={5}
            />
            {order.delivery?.failed_reason && (
              <div className="failure-box">
                <span>Last failed reason</span>
                <strong>{order.delivery.failed_reason}</strong>
                <small>Next action: {order.delivery.next_action || "—"}</small>
              </div>
            )}
            {order.proof_of_delivery_reference && (
              <div className="proof-box">
                <span>Proof of delivery reference</span>
                <strong>{order.proof_of_delivery_reference}</strong>
              </div>
            )}
          </section>
        </aside>
      </div>

      {modal === "attempt" && (
        <div className="order-modal-backdrop">
          <form className="order-modal" onSubmit={submitAttempt}>
            <h3>Record delivery attempt</h3>
            <p>
              Keep the reason concise so it can be reused in the operational
              timeline.
            </p>
            <label htmlFor="attemptReason">Reason</label>
            <input
              id="attemptReason"
              value={attemptReason}
              onChange={(event) => setAttemptReason(event.target.value)}
              placeholder="Recipient unavailable"
              required
            />
            <div className="order-modal-actions">
              <button
                type="button"
                onClick={() => {
                  setModal("");
                  setDeliveryPhoto(null);
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="primary"
                disabled={savingAction !== ""}
              >
                Save attempt
              </button>
            </div>
          </form>
        </div>
      )}

      {modal === "fail" && (
        <div className="order-modal-backdrop">
          <form className="order-modal" onSubmit={submitFailed}>
            <h3>Record failed delivery</h3>
            <p>
              This marks the shipment failed and stores the required next
              action.
            </p>
            <label htmlFor="failureReason">Failure reason</label>
            <input
              id="failureReason"
              value={failureReason}
              onChange={(event) => setFailureReason(event.target.value)}
              placeholder="Recipient unavailable"
              required
            />
            <label htmlFor="nextAction">Next action</label>
            <input
              id="nextAction"
              value={nextAction}
              onChange={(event) => setNextAction(event.target.value)}
              placeholder="Reschedule delivery"
              required
            />
            <div className="order-modal-actions">
              <button
                type="button"
                onClick={() => {
                  setModal("");
                  setDeliveryPhoto(null);
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="danger"
                disabled={savingAction !== ""}
              >
                Record failure
              </button>
            </div>
          </form>
        </div>
      )}

      {modal === "deliver" && (
        <div className="order-modal-backdrop">
          <form className="order-modal" onSubmit={submitDelivered}>
            <h3>Complete delivery</h3>
            <p>
              Record optional customer-facing notes and proof reference before
              closing the delivery.
            </p>
            <label htmlFor="customerNotes">Customer-facing delivery note</label>
            <textarea
              id="customerNotes"
              value={customerNotes}
              onChange={(event) => setCustomerNotes(event.target.value)}
              rows={3}
              placeholder="Left with recipient"
            />
            <label htmlFor="pod">Proof-of-delivery reference</label>
            <input
              id="pod"
              value={pod}
              onChange={(event) => setPod(event.target.value)}
              placeholder="Photo / signature reference"
            />
            <label htmlFor="deliveryPhoto">Completion photo *</label>
            <input
              id="deliveryPhoto"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              onChange={(event) =>
                setDeliveryPhoto(event.target.files?.[0] || null)
              }
              required
            />
            {deliveryPhotoPreview && (
              <div className="completion-upload-preview">
                <img
                  src={deliveryPhotoPreview}
                  alt="Selected delivery completion photo"
                />
                <span>{deliveryPhoto?.name}</span>
              </div>
            )}
            <div className="order-modal-actions">
              <button
                type="button"
                onClick={() => {
                  setModal("");
                  setDeliveryPhoto(null);
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="primary"
                disabled={savingAction !== ""}
              >
                Confirm delivered
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}
