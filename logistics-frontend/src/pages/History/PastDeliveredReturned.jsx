import { useCallback, useEffect, useMemo, useState } from "react";
import { FaBoxOpen, FaCheckCircle, FaRedoAlt, FaUndoAlt } from "react-icons/fa";

import { getCompletedHistory } from "../../services/logisticsService";
import "./pastDeliveredReturned.css";

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";
}

function ProductPreview({ item }) {
  if (!item) return null;
  return (
    <div className="history-item">
      <div className="history-item-image">
        {item.image_url ? (
          <img
            src={item.image_url}
            alt={item.product_name || "Product"}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <FaBoxOpen />
        )}
      </div>
      <div className="history-item-info">
        <strong>{item.product_name || "Product"}</strong>
        <span>
          {item.variant ? `${item.variant} · ` : ""}Qty {item.quantity || 0}
        </span>
        <small>SKU {item.sku || "—"}</small>
      </div>
    </div>
  );
}

function DeliveredCard({ record }) {
  return (
    <article className="history-record">
      <div className="history-record-head">
        <div>
          <span className="history-kicker">DELIVERY COMPLETED</span>
          <h2>Order #{record.order_id}</h2>
        </div>
        <span className="history-status delivered">
          <FaCheckCircle /> Delivered
        </span>
      </div>

      <div className="history-record-grid">
        <div className="history-details">
          <div className="history-detail-grid">
            <div>
              <span>Customer</span>
              <strong>{record.customer?.name || "—"}</strong>
            </div>
            <div>
              <span>Agent</span>
              <strong>{record.agent?.name || "—"}</strong>
            </div>
            <div>
              <span>Delivered</span>
              <strong>{formatDate(record.delivered_at)}</strong>
            </div>
            <div>
              <span>Destination</span>
              <strong>
                {[
                  record.destination?.city,
                  record.destination?.state,
                  record.destination?.postal_code,
                ]
                  .filter(Boolean)
                  .join(", ") || "—"}
              </strong>
            </div>
          </div>
          <div className="history-items">
            {record.items?.map((item) => (
              <ProductPreview key={item.id} item={item} />
            ))}
          </div>
          {record.customer_delivery_notes ? (
            <div className="history-note">
              <span>Customer delivery notes</span>
              <p>{record.customer_delivery_notes}</p>
            </div>
          ) : null}
          {record.proof_reference ? (
            <div className="history-note">
              <span>Proof reference</span>
              <p>{record.proof_reference}</p>
            </div>
          ) : null}
        </div>

        <div className="history-proof">
          <span>Completion photo</span>
          {record.proof_image_url ? (
            <a href={record.proof_image_url} target="_blank" rel="noreferrer">
              <img
                src={record.proof_image_url}
                alt={`Completion proof for order #${record.order_id}`}
                loading="lazy"
              />
            </a>
          ) : (
            <div className="history-no-photo">
              No completion photo recorded.
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function ReturnedCard({ record }) {
  return (
    <article className="history-record">
      <div className="history-record-head">
        <div>
          <span className="history-kicker">RETURN COMPLETED</span>
          <h2>Return #{record.return_id}</h2>
          <p>Order #{record.order_id}</p>
        </div>
        <span className="history-status returned">
          <FaUndoAlt /> Returned
        </span>
      </div>

      <div className="history-record-grid">
        <div className="history-details">
          <div className="history-detail-grid">
            <div>
              <span>Customer</span>
              <strong>{record.customer?.name || "—"}</strong>
            </div>
            <div>
              <span>Supplier</span>
              <strong>
                {record.supplier?.business_name || record.supplier?.name || "—"}
              </strong>
            </div>
            <div>
              <span>Agent</span>
              <strong>{record.agent?.name || "—"}</strong>
            </div>
            <div>
              <span>Received</span>
              <strong>{formatDate(record.returned_at)}</strong>
            </div>
          </div>
          <ProductPreview item={record.item} />
          {record.reason ? (
            <div className="history-note">
              <span>Customer return reason</span>
              <p>{record.reason}</p>
            </div>
          ) : null}
          {record.resolution_note ? (
            <div className="history-note">
              <span>Resolution</span>
              <p>{record.resolution_note}</p>
            </div>
          ) : null}
        </div>

        <div className="history-proof">
          <span>Completion photo</span>
          {record.completion_image_url ? (
            <a
              href={record.completion_image_url}
              target="_blank"
              rel="noreferrer"
            >
              <img
                src={record.completion_image_url}
                alt={`Completion proof for return #${record.return_id}`}
                loading="lazy"
              />
            </a>
          ) : (
            <div className="history-no-photo">
              No completion photo recorded.
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default function PastDeliveredReturned() {
  const [history, setHistory] = useState({ delivered: [], returned: [] });
  const [activeTab, setActiveTab] = useState("delivered");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async (silent = false) => {
    if (silent) setRefreshing(true);
    else setLoading(true);
    try {
      setError("");
      const data = await getCompletedHistory();
      setHistory({
        delivered: data?.delivered || [],
        returned: data?.returned || [],
      });
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          "Unable to load completed delivery history.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadHistory();
  }, [loadHistory]);

  const records = useMemo(
    () => (activeTab === "delivered" ? history.delivered : history.returned),
    [activeTab, history],
  );

  return (
    <section className="history-page">
      <div className="history-header">
        <div>
          <div className="history-kicker">OPERATIONS ARCHIVE</div>
          <h1>Past Delivered and Returned</h1>
          <p>
            Completed deliveries and supplier returns with their final product
            photo and operational details.
          </p>
        </div>
        <button
          type="button"
          className="history-refresh"
          onClick={() => loadHistory(true)}
          disabled={refreshing}
        >
          <FaRedoAlt className={refreshing ? "spinning" : ""} /> Refresh
        </button>
      </div>

      {error ? <div className="history-error">{error}</div> : null}

      <div
        className="history-tabs"
        role="tablist"
        aria-label="Completed logistics history"
      >
        <button
          type="button"
          className={activeTab === "delivered" ? "active" : ""}
          onClick={() => setActiveTab("delivered")}
        >
          <FaCheckCircle /> Past Delivered{" "}
          <span>{history.delivered.length}</span>
        </button>
        <button
          type="button"
          className={activeTab === "returned" ? "active" : ""}
          onClick={() => setActiveTab("returned")}
        >
          <FaUndoAlt /> Past Returned <span>{history.returned.length}</span>
        </button>
      </div>

      {loading ? (
        <div className="history-empty">
          <strong>Loading completed records…</strong>
        </div>
      ) : records.length === 0 ? (
        <div className="history-empty">
          <FaBoxOpen />
          <strong>No completed records yet</strong>
          <span>
            {activeTab === "delivered"
              ? "Completed customer deliveries will appear here."
              : "Completed supplier returns will appear here."}
          </span>
        </div>
      ) : (
        <div className="history-list">
          {records.map((record) =>
            activeTab === "delivered" ? (
              <DeliveredCard key={`delivered-${record.id}`} record={record} />
            ) : (
              <ReturnedCard key={`returned-${record.id}`} record={record} />
            ),
          )}
        </div>
      )}
    </section>
  );
}
