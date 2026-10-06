import { useQuery } from "@tanstack/react-query";
import { FiArrowRight, FiBox, FiTruck } from "react-icons/fi";
import { Link } from "react-router-dom";
import { getActiveOrders, getMyOrders } from "../../services/orderService";
import Container from "../../components/common/Container";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/common/AsyncState";
import { formatCurrency, formatDate } from "../../utils/formatters";
import { getApiMessage } from "../../utils/apiError";

function statusClass(status) {
  return `cc-order-status ${String(status || "").toLowerCase()}`;
}

function primaryShipment(order) {
  const shipments = Array.isArray(order?.shipments) ? order.shipments : [];
  return (
    shipments.find(
      (shipment) =>
        shipment?.awb_code ||
        shipment?.shiprocket_shipment_id ||
        shipment?.tracking_available,
    ) ||
    shipments[0] ||
    null
  );
}

function formatShipmentStatus(status) {
  return String(status || "Awaiting shipment").replaceAll("_", " ");
}

function formatEta(value) {
  if (!value) return "ETA not available yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "ETA not available yet";
  return `Estimated delivery: ${formatDate(date)}`;
}

function OrdersGrid({ orders }) {
  return (
    <div className="cc-order-list">
      {orders.map((order) => (
        <Link
          key={order.id}
          to={`/orders/${order.id}`}
          className="cc-order-card"
        >
          <div className="cc-order-card-top">
            <div>
              <strong>Order #{order.id}</strong>
              <span>{formatDate(order.created_at)}</span>
            </div>
            <span className={statusClass(order.status)}>
              {order.status.replaceAll("_", " ")}
            </span>
          </div>
          {(() => {
            const shipment = primaryShipment(order);
            if (!shipment) return null;
            return (
              <div
                className="cc-order-card-shipment"
                aria-label="Shipment summary"
              >
                <span>
                  <FiTruck />
                  {formatShipmentStatus(shipment.status)}
                </span>
                {shipment.courier_name ? (
                  <span>{shipment.courier_name}</span>
                ) : null}
                {shipment.awb_code ? (
                  <span>AWB: {shipment.awb_code}</span>
                ) : null}
                <span>{formatEta(shipment.estimated_delivery_at)}</span>
              </div>
            );
          })()}
          {order.items?.length ? (
            <div className="cc-order-card-products">
              {order.items.slice(0, 3).map((item) => (
                <span className="cc-order-card-product" key={item.id}>
                  <span className="cc-order-card-product-image">
                    {item.image ? (
                      <img
                        src={item.image}
                        alt=""
                        loading="lazy"
                        onError={(event) => {
                          event.currentTarget.style.display = "none";
                          event.currentTarget.nextElementSibling.style.display =
                            "grid";
                        }}
                      />
                    ) : null}
                    <FiBox style={{ display: item.image ? "none" : "grid" }} />
                  </span>
                  <span className="cc-order-card-product-name">
                    {item.product_name}
                  </span>
                </span>
              ))}
              {order.items.length > 3 ? (
                <span className="cc-order-card-product-more">
                  +{order.items.length - 3} more
                </span>
              ) : null}
            </div>
          ) : null}
          <div className="cc-order-card-bottom">
            <span>
              {order.items?.length || 0} item
              {order.items?.length === 1 ? "" : "s"}
            </span>
            <strong>{formatCurrency(order.total)}</strong>
            <FiArrowRight />
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function Orders() {
  const history = useQuery({ queryKey: ["orders"], queryFn: getMyOrders });
  const active = useQuery({
    queryKey: ["orders", "active"],
    queryFn: getActiveOrders,
  });
  const orders = Array.isArray(history.data) ? history.data : [];
  const activeOrders = Array.isArray(active.data) ? active.data : [];

  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-page-heading">
          <div>
            <span className="cc-eyebrow">Customer account</span>
            <h1>Your orders</h1>
            <p>
              Track active deliveries, review completed purchases and download
              invoices.
            </p>
          </div>
        </div>

        {history.isLoading || active.isLoading ? (
          <LoadingState label="Loading your orders…" />
        ) : history.isError ? (
          <ErrorState
            message={getApiMessage(
              history.error,
              "We couldn't load your orders.",
            )}
            onRetry={() => history.refetch()}
          />
        ) : (
          <>
            {activeOrders.length ? (
              <section className="cc-order-section">
                <div className="cc-card-head">
                  <div>
                    <h2>Current orders</h2>
                    <p>Orders still moving through fulfilment or delivery.</p>
                  </div>
                  <FiTruck />
                </div>
                <OrdersGrid orders={activeOrders} />
              </section>
            ) : null}

            {orders.length ? (
              <section className="cc-order-section">
                <div className="cc-card-head">
                  <div>
                    <h2>Order history</h2>
                    <p>
                      Every confirmed purchase remains linked to its invoice.
                    </p>
                  </div>
                </div>
                <OrdersGrid orders={orders} />
              </section>
            ) : (
              <EmptyState
                icon={<FiBox />}
                title="No orders yet"
                message="Your completed purchases will appear here."
                action={
                  <Link className="cc-btn primary" to="/products">
                    Start shopping
                  </Link>
                }
              />
            )}
          </>
        )}
      </Container>
    </div>
  );
}
