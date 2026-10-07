import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  FiArrowLeft,
  FiDownload,
  FiPackage,
  FiRotateCcw,
  FiXCircle,
} from "react-icons/fi";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  cancelOrder,
  downloadInvoice,
  getOrderDetails,
  getOrderTracking,
} from "../../services/orderService";
import { createReturn } from "../../services/returnsService";
import Container from "../../components/common/Container";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/common/AsyncState";
import { formatCurrency, formatDateTime } from "../../utils/formatters";
import { getApiMessage } from "../../utils/apiError";
import OrderReviewSection from "../../components/order/OrderReviewSection";

function statusLabel(value) {
  return String(value || "").replaceAll("_", " ");
}

function shipmentStatusLabel(value) {
  return String(value || "Awaiting shipment")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function returnStatusLabel(value) {
  return (
    {
      REQUESTED: "Return requested",
      PICKUP_ASSIGNED: "Pickup assigned",
      PICKED_UP: "Picked up",
      IN_TRANSIT: "Returning to supplier",
      OUT_FOR_DELIVERY: "Out for delivery to supplier",
      FAILED: "Delivery delayed",
      RECEIVED: "Delivered to supplier",
      CANCELLED: "Cancelled",
    }[value] || statusLabel(value)
  );
}

export default function OrderDetails() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [cancelReason, setCancelReason] = useState("");
  const [returningItem, setReturningItem] = useState(null);
  const [returnReason, setReturnReason] = useState("");
  const [message, setMessage] = useState("");
  const [trackingRefresh, setTrackingRefresh] = useState(false);
  const query = useQuery({
    queryKey: ["orders", orderId],
    queryFn: () => getOrderDetails(orderId),
  });
  const trackingQuery = useQuery({
    queryKey: ["orders", orderId, "tracking"],
    queryFn: () => getOrderTracking(orderId),
    enabled: Boolean(orderId),
    staleTime: 60 * 1000,
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelOrder(orderId, cancelReason),
    onSuccess: () => {
      setMessage("Cancellation recorded.");
      client.invalidateQueries({ queryKey: ["orders"] });
      client.invalidateQueries({ queryKey: ["orders", "active"] });
      client.invalidateQueries({ queryKey: ["orders", orderId] });
    },
  });

  const returnMutation = useMutation({
    mutationFn: () =>
      createReturn({
        order_id: Number(orderId),
        order_item_id: Number(returningItem),
        reason: returnReason,
      }),
    onSuccess: () => {
      setMessage("Return request submitted.");
      setReturningItem(null);
      setReturnReason("");
      client.invalidateQueries({ queryKey: ["orders", orderId] });
    },
  });

  if (query.isLoading)
    return (
      <div className="cc-page-shell">
        <Container>
          <LoadingState label="Loading order…" />
        </Container>
      </div>
    );
  if (query.isError)
    return (
      <div className="cc-page-shell">
        <Container>
          <ErrorState
            message={getApiMessage(query.error, "Unable to load this order.")}
            onRetry={() => query.refetch()}
          />
        </Container>
      </div>
    );
  if (!query.data)
    return (
      <div className="cc-page-shell">
        <Container>
          <EmptyState
            title="Order not found"
            message="This order may no longer be available for your account."
            action={
              <Link className="cc-btn primary" to="/orders">
                Back to orders
              </Link>
            }
          />
        </Container>
      </div>
    );

  const order = query.data;
  const shipments = Array.isArray((trackingQuery.data || order).shipments)
    ? (trackingQuery.data || order).shipments
    : [];
  const canCancel = ["PAID", "PROCESSING"].includes(order.status);
  const canReturn = order.status === "DELIVERED";

  async function handleInvoice() {
    try {
      const blob = await downloadInvoice(order.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${order.invoice?.invoice_number || `clipcart-order-${order.id}`}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setMessage(getApiMessage(err, "Invoice download failed."));
    }
  }

  function handleCancel() {
    cancelMutation.mutate();
  }

  function handleReturnSubmit(event) {
    event.preventDefault();
    if (!returningItem || !returnReason.trim()) return;
    returnMutation.mutate();
  }

  return (
    <div className="cc-page-shell">
      <Container>
        <button
          type="button"
          className="cc-link-button"
          onClick={() => navigate("/orders")}
        >
          <FiArrowLeft /> Back to orders
        </button>
        <div className="cc-order-detail-head">
          <div>
            <span className="cc-eyebrow">Order #{order.id}</span>
            <h1>Order details</h1>
            <p>{formatDateTime(order.created_at)}</p>
          </div>
          <span
            className={`cc-order-status large ${String(order.status).toLowerCase()}`}
          >
            {statusLabel(order.status)}
          </span>
        </div>

        {message ? (
          <div className="cc-inline-message" role="status">
            {message}
          </div>
        ) : null}
        {cancelMutation.isError ? (
          <div className="cc-form-error">
            {getApiMessage(
              cancelMutation.error,
              "Unable to cancel this order.",
            )}
          </div>
        ) : null}
        {returnMutation.isError ? (
          <div className="cc-form-error">
            {getApiMessage(
              returnMutation.error,
              "Unable to create the return request.",
            )}
          </div>
        ) : null}

        <div className="cc-order-detail-grid">
          <section className="cc-detail-panel">
            <div className="cc-card-head">
              <div>
                <h2>Items</h2>
                <p>Purchased variants and fixed order-time prices.</p>
              </div>
            </div>
            <div className="cc-order-items">
              {(order.items || []).map((item) => {
                const productId = item.product_id || item.product?.id;

                const openProduct = () => {
                  if (productId) navigate(`/product/${productId}`);
                };

                const handleItemKeyDown = (event) => {
                  if (!productId) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openProduct();
                  }
                };

                const handleItemClick = (event) => {
                  if (!productId) return;
                  if (
                    event.target.closest("button, a, input, textarea, select")
                  ) {
                    return;
                  }
                  openProduct();
                };

                return (
                  <article
                    className={`cc-order-item${productId ? " is-clickable" : ""}`}
                    key={item.id}
                    role={productId ? "link" : undefined}
                    tabIndex={productId ? 0 : undefined}
                    onClick={productId ? handleItemClick : undefined}
                    onKeyDown={productId ? handleItemKeyDown : undefined}
                  >
                    <div className="cc-order-item-media">
                      {item.image ? (
                        <img
                          src={item.image}
                          alt={item.product_name || "Product"}
                          loading="lazy"
                          onError={(event) => {
                            event.currentTarget.style.display = "none";
                            event.currentTarget.nextElementSibling.style.display =
                              "grid";
                          }}
                        />
                      ) : null}
                      <FiPackage
                        style={{ display: item.image ? "none" : "grid" }}
                      />
                    </div>
                    <div>
                      <strong>{item.product_name}</strong>
                      <p>
                        {item.variant_value || "Standard item"} · Qty{" "}
                        {item.quantity}
                      </p>
                    </div>
                    <div className="cc-order-item-price">
                      <span>{formatCurrency(item.unit_price)}</span>
                      <strong>{formatCurrency(item.subtotal)}</strong>
                    </div>
                    {canReturn ? (
                      <button
                        type="button"
                        className="cc-link-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setReturningItem(item.id);
                        }}
                      >
                        <FiRotateCcw /> Return
                      </button>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </section>

          <aside className="cc-summary-card">
            <h2>Payment summary</h2>
            <div className="cc-summary-lines">
              <span>
                Subtotal <strong>{formatCurrency(order.subtotal)}</strong>
              </span>
              <span>
                Discount <strong>− {formatCurrency(order.discount)}</strong>
              </span>
              <span>
                Marketing fee{" "}
                <strong>{formatCurrency(order.marketing_fee)}</strong>
              </span>
              <span>
                Tax <strong>{formatCurrency(order.tax)}</strong>
              </span>
              <span className="total">
                Total <strong>{formatCurrency(order.total)}</strong>
              </span>
            </div>
            <p className="cc-summary-note">
              Payment: {statusLabel(order.payment_status)}
            </p>
            {order.invoice ? (
              <button
                type="button"
                className="cc-btn secondary full"
                onClick={handleInvoice}
              >
                <FiDownload /> Download invoice
              </button>
            ) : null}
            {canCancel ? (
              <>
                <textarea
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Cancellation reason (optional)"
                  rows={2}
                />
                <button
                  type="button"
                  className="cc-btn secondary full"
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                >
                  <FiXCircle />{" "}
                  {cancelMutation.isPending ? "Cancelling…" : "Cancel order"}
                </button>
              </>
            ) : null}
            {order.status === "DELIVERED" ? (
              <OrderReviewSection order={order} />
            ) : null}
          </aside>
        </div>

        {(order.returns || []).length ? (
          <section className="cc-detail-panel cc-return-journey-panel">
            <div className="cc-card-head">
              <div>
                <h2>Return journey</h2>
                <p>
                  Logistics picks the item up from your delivery address and
                  sends it back to the supplier.
                </p>
              </div>
            </div>
            <div className="cc-return-journey-grid">
              {(order.returns || []).map((request) => (
                <article
                  className="cc-return-journey-card"
                  key={`journey-${request.id}`}
                >
                  <div className="cc-return-journey-top">
                    <strong>Return #{request.id}</strong>
                    <span
                      className={`cc-return-status ${String(request.status || "").toLowerCase()}`}
                    >
                      {returnStatusLabel(request.status)}
                    </span>
                  </div>
                  <div className="cc-return-steps">
                    <span
                      className={
                        request.delivery?.stage === "AWAITING_PICKUP"
                          ? "current"
                          : ""
                      }
                    >
                      1. Pickup from you
                    </span>
                    <span
                      className={
                        [
                          "PICKUP_ASSIGNED",
                          "PICKED_UP",
                          "IN_TRANSIT",
                          "OUT_FOR_DELIVERY",
                          "RECEIVED",
                        ].includes(request.status)
                          ? "current"
                          : ""
                      }
                    >
                      2. In transit
                    </span>
                    <span
                      className={
                        request.status === "OUT_FOR_DELIVERY" ? "current" : ""
                      }
                    >
                      3. Delivery to supplier
                    </span>
                    <span
                      className={
                        request.status === "RECEIVED" ? "current done" : ""
                      }
                    >
                      4. Supplier received
                    </span>
                  </div>
                  {request.delivery?.supplier ? (
                    <div className="cc-return-destination">
                      <strong>Return destination</strong>
                      <span>
                        {request.delivery.supplier.business_name ||
                          request.delivery.supplier.name ||
                          "Supplier"}
                      </span>
                      <small>
                        {[
                          request.delivery.supplier.address_line_1,
                          request.delivery.supplier.address_line_2,
                          request.delivery.supplier.city,
                          request.delivery.supplier.state,
                          request.delivery.supplier.postal_code,
                        ]
                          .filter(Boolean)
                          .join(", ") ||
                          "Supplier return address not configured."}
                      </small>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {returningItem ? (
          <section className="cc-detail-panel">
            <h2>Request a return</h2>
            <form className="cc-form compact" onSubmit={handleReturnSubmit}>
              <textarea
                required
                minLength={5}
                value={returnReason}
                onChange={(e) => setReturnReason(e.target.value)}
                rows={4}
                placeholder="Tell us why you want to return this item."
              />
              <div className="cc-inline-actions">
                <button
                  type="submit"
                  className="cc-btn primary"
                  disabled={returnMutation.isPending}
                >
                  {returnMutation.isPending
                    ? "Submitting…"
                    : "Submit return request"}
                </button>
                <button
                  type="button"
                  className="cc-btn secondary"
                  onClick={() => setReturningItem(null)}
                >
                  Close
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="cc-detail-panel cc-order-tracking-panel">
          <div className="cc-card-head">
            <div>
              <span className="cc-shipment-eyebrow">Shipping & delivery</span>
              <h2>Courier shipments</h2>
              <p>Live forward-delivery information from Shiprocket.</p>
            </div>
            {shipments.length ? (
              <button
                type="button"
                className="cc-btn secondary"
                disabled={trackingQuery.isFetching || trackingRefresh}
                onClick={async () => {
                  setTrackingRefresh(true);
                  setMessage("");
                  try {
                    const data = await getOrderTracking(orderId, true);
                    client.setQueryData(["orders", orderId, "tracking"], data);
                  } catch (err) {
                    setMessage(
                      getApiMessage(
                        err,
                        "Unable to refresh Shiprocket tracking right now.",
                      ),
                    );
                  } finally {
                    setTrackingRefresh(false);
                  }
                }}
              >
                {trackingQuery.isFetching || trackingRefresh
                  ? "Refreshing…"
                  : "Refresh tracking"}
              </button>
            ) : null}
          </div>

          {shipments.length ? (
            <div className="cc-shipment-list">
              {shipments.map((shipment) => (
                <article key={shipment.id} className="cc-shipment-card">
                  <div className="cc-shipment-card-head">
                    <div>
                      <span className="cc-shipment-label">
                        Shipment #{shipment.id}
                      </span>
                      <h3>{shipment.courier_name || "Courier shipment"}</h3>
                    </div>
                    <span className="cc-order-status large">
                      {shipmentStatusLabel(shipment.status)}
                    </span>
                  </div>

                  <div className="cc-shipment-meta">
                    <div>
                      <span>AWB</span>
                      <strong>
                        {shipment.awb_code || "Awaiting assignment"}
                      </strong>
                    </div>
                    <div>
                      <span>Estimated delivery</span>
                      <strong>
                        {shipment.estimated_delivery_at
                          ? formatDateTime(shipment.estimated_delivery_at)
                          : "Not available yet"}
                      </strong>
                    </div>
                    <div>
                      <span>Last synced</span>
                      <strong>
                        {shipment.last_synced_at
                          ? formatDateTime(shipment.last_synced_at)
                          : "Not synced yet"}
                      </strong>
                    </div>
                  </div>

                  {Array.isArray(shipment.tracking_events) &&
                  shipment.tracking_events.length ? (
                    <div className="cc-shipment-events">
                      <div className="cc-shipment-events-head">
                        <strong>Latest tracking events</strong>
                        <span>
                          {Math.min(shipment.tracking_events.length, 6)} shown
                        </span>
                      </div>
                      <div className="cc-shipment-event-list">
                        {shipment.tracking_events
                          .slice(-6)
                          .reverse()
                          .map((event, index) => (
                            <div
                              className="cc-shipment-event"
                              key={`${shipment.id}-${index}`}
                            >
                              <span className="cc-shipment-event-dot">
                                <FiPackage />
                              </span>
                              <div>
                                <strong>
                                  {event.status ||
                                    event.activity ||
                                    event.current_status ||
                                    "Shipment update"}
                                </strong>
                                <p>
                                  {event.location ||
                                    event.activity ||
                                    event.details ||
                                    "Shiprocket tracking update"}
                                </p>
                                <small>
                                  {formatDateTime(
                                    event.date ||
                                      event.event_date ||
                                      event.timestamp,
                                  )}
                                </small>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  ) : null}

                  <div className="cc-shipment-actions">
                    {shipment.tracking_url ? (
                      <a
                        className="cc-btn secondary"
                        href={shipment.tracking_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Track shipment
                      </a>
                    ) : null}
                    {shipment.delivered_at ? (
                      <span className="cc-shipment-delivered">
                        Delivered {formatDateTime(shipment.delivered_at)}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="cc-shipment-empty">
              <FiPackage />
              <strong>Shipment provisioning is pending.</strong>
              <span>
                Shipment details will appear here once the supplier starts
                processing the order.
              </span>
            </div>
          )}
        </section>

        {order.delivery ? (
          <section className="cc-detail-panel">
            <h2>Delivery address</h2>
            <p>
              {order.delivery.full_name} · {order.delivery.phone}
            </p>
            <p>
              {order.delivery.address_line_1}
              {order.delivery.address_line_2
                ? `, ${order.delivery.address_line_2}`
                : ""}
            </p>
            <p>
              {order.delivery.city}, {order.delivery.state}{" "}
              {order.delivery.postal_code}
            </p>
          </section>
        ) : null}

        {(order.returns || []).length ? (
          <section className="cc-detail-panel">
            <div className="cc-card-head">
              <div>
                <h2>Return requests</h2>
                <p>
                  Customer-visible status for return requests recorded by the
                  backend.
                </p>
              </div>
            </div>
            <div className="space-y-3">
              {(order.returns || []).map((request) => (
                <article key={request.id} className="cc-return-request-card">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <strong>Return #{request.id}</strong>
                    <span className="cc-order-status">
                      {statusLabel(request.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-300">{request.reason}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    Requested {formatDateTime(request.created_at)}
                    {request.resolved_at
                      ? ` · Resolved ${formatDateTime(request.resolved_at)}`
                      : ""}
                  </p>
                  {request.resolution_note ? (
                    <p className="mt-2 text-sm text-gray-400">
                      {request.resolution_note}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </Container>
    </div>
  );
}
