import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  FaArrowLeft,
  FaBoxOpen,
  FaMapMarkerAlt,
  FaPhone,
  FaPrint,
  FaUser,
} from "react-icons/fa";
import {
  getSupplierOrderDetails,
  updateSupplierOrderStatus,
} from "../../services/orderService";
import { formatDateTime, money } from "../../utils/dateRange";
import "../../styles/supplier-pages.css";

export default function OrderDetails() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updating, setUpdating] = useState(false);
  async function load() {
    setLoading(true);
    try {
      setError("");
      setOrder(await getSupplierOrderDetails(orderId));
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load order.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, [orderId]); // eslint-disable-line react-hooks/exhaustive-deps
  async function process() {
    setUpdating(true);
    try {
      await updateSupplierOrderStatus(orderId, "PROCESSING");
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to update order.");
    } finally {
      setUpdating(false);
    }
  }
  if (loading)
    return (
      <div className="page-shell">
        <div className="panel empty-state">Loading order…</div>
      </div>
    );
  if (!order)
    return (
      <div className="page-shell">
        <div className="notice error">{error || "Order not found."}</div>
        <Link className="ghost-link" to="/orders">
          <FaArrowLeft /> Back to orders
        </Link>
      </div>
    );
  const canProcess = order.status === "PAID";
  const delivery = order.delivery || {};
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <div className="breadcrumb">
            <Link to="/orders">Orders</Link>
            <span>/</span>#{order.id}
          </div>
          <h2>Order #{order.id}</h2>
          <p>Supplier fulfillment view for your order items only.</p>
        </div>
        <div className="heading-actions">
          <button className="ghost-link" onClick={() => window.print()}>
            <FaPrint /> Print PO
          </button>
          <Link className="ghost-link" to="/orders">
            <FaArrowLeft /> Back
          </Link>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      <div className="detail-status-row">
        <div>
          <span className="muted">Current status</span>
          <strong className="detail-status">{order.status}</strong>
        </div>
        {canProcess && (
          <button className="action-link" onClick={process} disabled={updating}>
            {updating ? "Updating…" : "Start processing"}
          </button>
        )}
        <div className="fulfillment-note">
          Suppliers can move a paid order into processing. Shipment and delivery
          are controlled by logistics.
        </div>
      </div>
      <div className="detail-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">
                <FaUser /> Delivery contact
              </h3>
              <p className="panel-subtitle">
                Information required to fulfill the shipment.
              </p>
            </div>
          </div>
          <div className="detail-body">
            <p>
              <b>{delivery.full_name || order.customer?.name || "—"}</b>
            </p>
            <p>
              <FaPhone /> {delivery.phone || "—"}
            </p>
            <p>
              <FaMapMarkerAlt /> {address(delivery)}
            </p>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Order information</h3>
              <p className="panel-subtitle">
                Supplier-relevant order totals and timestamps.
              </p>
            </div>
          </div>
          <div className="detail-body">
            <div className="detail-line">
              <span>Order total</span>
              <b>{money(order.supplier_total)}</b>
            </div>
            <div className="detail-line">
              <span>Units</span>
              <b>{order.units}</b>
            </div>
            <div className="detail-line">
              <span>Payment</span>
              <b>{order.payment_status}</b>
            </div>
            <div className="detail-line">
              <span>Placed</span>
              <b>{formatDateTime(order.created_at)}</b>
            </div>
          </div>
        </section>
      </div>
      <section className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">
              <FaBoxOpen /> Supplier items
            </h3>
            <p className="panel-subtitle">
              Only products owned by the signed-in supplier are exposed.
            </p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Variant</th>
                <th>SKU</th>
                <th>Qty</th>
                <th>Unit price</th>
                <th>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {(order.items || []).map((i) => (
                <tr key={i.id}>
                  <td>
                    <div className="supplier-order-item-product">
                      <span className="supplier-order-item-image">
                        {i.image ? (
                          <img
                            src={i.image}
                            alt=""
                            loading="lazy"
                            onError={(event) => {
                              event.currentTarget.style.display = "none";
                              event.currentTarget.nextElementSibling.style.display =
                                "grid";
                            }}
                          />
                        ) : null}
                        <FaBoxOpen
                          style={{ display: i.image ? "none" : "grid" }}
                        />
                      </span>
                      <b>{i.product_name}</b>
                    </div>
                  </td>
                  <td>{i.variant_value || i.variant_name || "—"}</td>
                  <td>{i.sku || "—"}</td>
                  <td>{i.quantity}</td>
                  <td>{money(i.unit_price)}</td>
                  <td>{money(i.subtotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="supplier-total">
          <span>Supplier order value</span>
          <strong>{money(order.supplier_total)}</strong>
        </div>
      </section>
      <section className="panel printable-po">
        <div className="po-header">
          <div>
            <div className="brand-mark print-brand">
              CLIPCART <span>SUPPLIER FULFILLMENT</span>
            </div>
            <h3>Purchase / Fulfillment Order</h3>
          </div>
          <div className="po-meta">
            <b>PO #{order.id}</b>
            <span>{formatDateTime(order.created_at)}</span>
          </div>
        </div>
        <div className="po-grid">
          <div>
            <small>Ship to</small>
            <p>
              <b>{delivery.full_name}</b>
              <br />
              {address(delivery)}
              <br />
              {delivery.phone}
            </p>
          </div>
          <div>
            <small>Fulfillment</small>
            <p>
              Status: <b>{order.status}</b>
              <br />
              Expected:{" "}
              {order.delivery_expectation?.window || "3–7 business days"}
            </p>
          </div>
        </div>
        <table className="po-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>SKU</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {(order.items || []).map((i) => (
              <tr key={i.id}>
                <td>
                  {i.product_name}
                  {i.variant_value ? ` · ${i.variant_value}` : ""}
                </td>
                <td>{i.sku || "—"}</td>
                <td>{i.quantity}</td>
                <td>{money(i.unit_price)}</td>
                <td>{money(i.subtotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="po-total">
          Supplier total: <b>{money(order.supplier_total)}</b>
        </div>
      </section>
    </div>
  );
}
function address(d) {
  return (
    [
      d.address_line_1,
      d.address_line_2,
      d.landmark,
      d.city,
      d.state,
      d.postal_code,
      d.country,
    ]
      .filter(Boolean)
      .join(", ") || "Delivery address unavailable."
  );
}
