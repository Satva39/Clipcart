import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  FaArrowLeft,
  FaBoxOpen,
  FaCreditCard,
  FaMapMarkerAlt,
  FaUser,
} from "react-icons/fa";

import {
  getAdminOrder,
  getShiprocketDiagnostics,
  retryAdminShipment,
} from "../services/orderService";

export default function OrderDetails() {
  const { orderId } = useParams();

  const [order, setOrder] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [shiprocketDiagnostics, setShiprocketDiagnostics] = useState(null);

  useEffect(() => {
    async function loadOrder() {
      try {
        setLoading(true);
        setError("");

        const data = await getAdminOrder(orderId);

        setOrder(data);
      } catch (err) {
        setError(err?.response?.data?.message || "Unable to load order.");
      } finally {
        setLoading(false);
      }
    }

    loadOrder();
  }, [orderId]);

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-empty">Loading order...</div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="admin-page">
        <Link to="/orders" className="admin-back-link">
          <FaArrowLeft />
          Back to Orders
        </Link>

        <div className="admin-error">{error || "Order not found."}</div>
      </div>
    );
  }

  async function checkShiprocket() {
    try {
      setShiprocketDiagnostics(await getShiprocketDiagnostics(orderId));
    } catch (err) {
      setShiprocketDiagnostics({
        configured: false,
        error:
          err?.response?.data?.message ||
          "Unable to check Shiprocket configuration.",
      });
    }
  }

  async function retryShipments() {
    try {
      setRetrying(true);
      setError("");
      await retryAdminShipment(orderId);
      const data = await getAdminOrder(orderId);
      setOrder(data);
    } catch (err) {
      setError(
        err?.response?.data?.message || "Unable to retry courier shipment.",
      );
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="admin-page">
      <Link to="/orders" className="admin-back-link">
        <FaArrowLeft />
        Back to Orders
      </Link>

      <div className="admin-page-header">
        <div>
          <span className="admin-eyebrow">ORDER DETAILS</span>

          <h1>Order #{order.id}</h1>

          <p>Complete platform order information.</p>
        </div>

        <span
          className={`admin-order-status admin-order-${String(
            order.status,
          ).toLowerCase()}`}
        >
          {order.status}
        </span>
      </div>

      <div className="admin-detail-grid">
        <section className="admin-detail-card">
          <div className="admin-detail-title">
            <FaUser />
            <h2>Customer</h2>
          </div>

          <p>
            <strong>{order.customer?.name || "—"}</strong>
          </p>

          <p>{order.customer?.email || "—"}</p>

          <p>{order.customer?.phone || "No phone"}</p>
        </section>

        <section className="admin-detail-card">
          <div className="admin-detail-title">
            <FaMapMarkerAlt />
            <h2>Delivery Address</h2>
          </div>

          {order.address ? (
            <>
              <p>
                <strong>{order.address.full_name}</strong>
              </p>

              <p>{order.address.address_line_1}</p>

              {order.address.address_line_2 && (
                <p>{order.address.address_line_2}</p>
              )}

              <p>
                {order.address.city}, {order.address.state}
              </p>

              <p>
                {order.address.postal_code}, {order.address.country}
              </p>
            </>
          ) : (
            <p>No address available.</p>
          )}
        </section>

        <section className="admin-detail-card">
          <div className="admin-detail-title">
            <FaCreditCard />
            <h2>Payment</h2>
          </div>

          {order.payment ? (
            <>
              <p>
                Status: <strong>{order.payment.status}</strong>
              </p>

              <p>Gateway: {order.payment.gateway}</p>

              <p>Type: {order.payment.payment_type}</p>

              <p>Transaction: {order.payment.transaction_id || "—"}</p>
            </>
          ) : (
            <p>No payment record.</p>
          )}
        </section>

        <section className="admin-detail-card">
          <div className="admin-detail-title">
            <FaBoxOpen />
            <h2>Order Summary</h2>
          </div>

          <div className="admin-total-row">
            <span>Subtotal</span>
            <strong>₹{Number(order.subtotal).toLocaleString("en-IN")}</strong>
          </div>

          <div className="admin-total-row">
            <span>Discount</span>
            <strong>₹{Number(order.discount).toLocaleString("en-IN")}</strong>
          </div>

          <div className="admin-total-row admin-grand-total">
            <span>Total</span>
            <strong>₹{Number(order.total).toLocaleString("en-IN")}</strong>
          </div>
        </section>
      </div>

      {shiprocketDiagnostics && (
        <section className="admin-detail-card admin-items-card">
          <div className="admin-detail-title">
            <FaBoxOpen />
            <h2>Shiprocket Diagnostics</h2>
          </div>
          <div className="admin-empty" style={{ textAlign: "left" }}>
            <strong>
              {shiprocketDiagnostics.error ||
                (shiprocketDiagnostics.authentication?.ok
                  ? "Shiprocket authentication is working."
                  : "Shiprocket configuration needs attention.")}
            </strong>
            <div>
              Authentication:{" "}
              {shiprocketDiagnostics.authentication?.ok ? "OK" : "FAILED"}
            </div>
            <div>
              Orders API:{" "}
              {shiprocketDiagnostics.orders_api?.ok ? "OK" : "FAILED"}
            </div>
            <div>
              Pickup API:{" "}
              {shiprocketDiagnostics.pickup_api?.ok
                ? `OK (${shiprocketDiagnostics.pickup_api.count} locations)`
                : "FAILED"}
            </div>
            {shiprocketDiagnostics.order?.ok && (
              <div>
                Local Clipcart shipments:{" "}
                {shiprocketDiagnostics.order.local_shipments?.length || 0}
              </div>
            )}
            {shiprocketDiagnostics.external_matches?.length > 0 && (
              <div>
                External order lookup:{" "}
                {shiprocketDiagnostics.external_matches.some(
                  (item) => item.found,
                )
                  ? "FOUND"
                  : "NOT FOUND"}
              </div>
            )}
          </div>
        </section>
      )}

      <section className="admin-detail-card admin-items-card">
        <div className="admin-detail-title">
          <FaBoxOpen />
          <h2>Courier Shipments</h2>
          <button
            type="button"
            className="admin-secondary-btn"
            onClick={checkShiprocket}
            style={{ marginLeft: "auto" }}
          >
            Check Shiprocket
          </button>
          <button
            type="button"
            className="admin-primary-btn"
            onClick={retryShipments}
            disabled={retrying}
          >
            {retrying ? "Retrying…" : "Retry failed shipments"}
          </button>
        </div>
        {order.shipments?.length ? (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th>Status</th>
                  <th>Courier</th>
                  <th>AWB</th>
                  <th>Reference</th>
                  <th>Failure</th>
                  <th>Last sync</th>
                </tr>
              </thead>
              <tbody>
                {order.shipments.map((shipment) => (
                  <tr key={shipment.id}>
                    <td>
                      {shipment.supplier?.business_name ||
                        shipment.supplier?.name ||
                        "—"}
                    </td>
                    <td>{shipment.status || "—"}</td>
                    <td>{shipment.courier_name || "Awaiting assignment"}</td>
                    <td>{shipment.awb_code || "Awaiting assignment"}</td>
                    <td>
                      {shipment.reference_id ||
                        shipment.shiprocket_reference_id ||
                        "—"}
                    </td>
                    <td>{shipment.failure_message || "—"}</td>
                    <td>
                      {shipment.last_synced_at
                        ? new Date(shipment.last_synced_at).toLocaleString(
                            "en-IN",
                          )
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="admin-empty">
            No Shiprocket shipment record exists yet.
          </div>
        )}
      </section>

      <section className="admin-detail-card admin-items-card">
        <div className="admin-detail-title">
          <FaBoxOpen />
          <h2>Order Items</h2>
        </div>

        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Subtotal</th>
              </tr>
            </thead>

            <tbody>
              {order.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.product_name}</strong>

                    {item.variant_name && <span>{item.variant_name}</span>}
                  </td>

                  <td>{item.quantity}</td>

                  <td>₹{Number(item.unit_price).toLocaleString("en-IN")}</td>

                  <td>₹{Number(item.subtotal).toLocaleString("en-IN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
