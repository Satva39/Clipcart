import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  FaArrowRight,
  FaFilter,
  FaRedoAlt,
  FaSearch,
  FaTruck,
} from "react-icons/fa";

import { getQueue, getReturns } from "../../services/logisticsService";
import "./deliveryQueue.css";

const stages = [
  ["", "All stages"],
  ["AWAITING_PICKUP", "Awaiting pickup"],
  ["PICKUP_ASSIGNED", "Pickup assigned"],
  ["IN_TRANSIT", "In transit"],
  ["OUT_FOR_DELIVERY", "Out for delivery"],
  ["FAILED", "Failed"],
  ["DELIVERED", "Delivered"],
];

const statusOptions = [
  ["", "All statuses"],
  ["PROCESSING", "Supplier handoff"],
  ["SHIPPED", "Shipped / in transit"],
  ["OUT_FOR_DELIVERY", "Out for delivery"],
  ["DELIVERED", "Delivered"],
  ["FAILED", "Failed"],
];

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";
}

function statusClass(stage) {
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

export default function DeliveryQueue() {
  const [filters, setFilters] = useState({
    search: "",
    stage: "",
    status: "",
    date: "",
    agent: "",
    pending_action: "",
  });
  const [draft, setDraft] = useState(filters);
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const knownIds = useRef(new Set());
  const [newOrderCount, setNewOrderCount] = useState(0);
  const [returns, setReturns] = useState([]);

  const loadQueue = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      else setRefreshing(true);

      try {
        setError("");
        const [data, returnData] = await Promise.all([
          getQueue(filters),
          getReturns(),
        ]);
        const newIds = data
          .map((item) => item.order_id)
          .filter((id) => !knownIds.current.has(id));

        if (knownIds.current.size > 0 && newIds.length) {
          setNewOrderCount((current) => current + newIds.length);
        }
        knownIds.current = new Set(data.map((item) => item.order_id));
        setQueue(data);
        setReturns(returnData);
      } catch (err) {
        setError(
          err?.response?.data?.message || "Unable to load the delivery queue.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [filters],
  );

  useEffect(() => {
    knownIds.current = new Set();
  }, [filters]);

  useEffect(() => {
    // Initial load is intentionally performed in the effect; the callback owns async state reconciliation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadQueue();
    const interval = window.setInterval(() => loadQueue(true), 12000);
    return () => window.clearInterval(interval);
  }, [loadQueue]);

  const activeFilterCount = useMemo(
    () =>
      Object.values(filters).filter((value) => String(value || "").trim())
        .length,
    [filters],
  );

  function applyFilters(event) {
    event.preventDefault();
    setFilters(draft);
    setNewOrderCount(0);
  }

  function resetFilters() {
    const empty = {
      search: "",
      stage: "",
      status: "",
      date: "",
      agent: "",
      pending_action: "",
    };
    setDraft(empty);
    setFilters(empty);
    setNewOrderCount(0);
  }

  return (
    <section className="queue-page">
      <div className="queue-header">
        <div>
          <div className="queue-kicker">OPERATIONS WORKSPACE</div>
          <h1>Delivery queue</h1>
          <p>
            Work the current shipment pipeline from supplier handoff through
            last-mile delivery.
          </p>
        </div>

        <button
          type="button"
          className="queue-refresh-button"
          onClick={() => loadQueue(true)}
          disabled={refreshing}
        >
          <FaRedoAlt className={refreshing ? "spinning" : ""} />
          Refresh
        </button>
      </div>

      {newOrderCount > 0 && (
        <div className="queue-alert-banner">
          <div>
            <strong>
              {newOrderCount} new order{newOrderCount === 1 ? "" : "s"} entered
              the queue.
            </strong>
            <span>Live polling detected real backend state changes.</span>
          </div>
          <button type="button" onClick={() => setNewOrderCount(0)}>
            Dismiss
          </button>
        </div>
      )}

      {error && <div className="queue-error">{error}</div>}

      <form className="queue-filters" onSubmit={applyFilters}>
        <div className="queue-search">
          <FaSearch />
          <input
            value={draft.search}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                search: event.target.value,
              }))
            }
            placeholder="Search order, recipient, phone, city or PIN"
          />
        </div>

        <select
          value={draft.stage}
          onChange={(event) =>
            setDraft((current) => ({ ...current, stage: event.target.value }))
          }
        >
          {stages.map(([value, label]) => (
            <option value={value} key={value || "all-stage"}>
              {label}
            </option>
          ))}
        </select>

        <select
          value={draft.status}
          onChange={(event) =>
            setDraft((current) => ({ ...current, status: event.target.value }))
          }
        >
          {statusOptions.map(([value, label]) => (
            <option value={value} key={value || "all-status"}>
              {label}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={draft.date}
          onChange={(event) =>
            setDraft((current) => ({ ...current, date: event.target.value }))
          }
          aria-label="Filter by order date"
        />

        <input
          value={draft.agent}
          onChange={(event) =>
            setDraft((current) => ({ ...current, agent: event.target.value }))
          }
          placeholder="Agent"
        />

        <select
          value={draft.pending_action}
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              pending_action: event.target.value,
            }))
          }
        >
          <option value="">All pending actions</option>
          <option value="ASSIGN">Assignment</option>
          <option value="PICKUP">Pickup</option>
          <option value="OUT FOR DELIVERY">Dispatch</option>
          <option value="COMPLETE">Delivery completion</option>
          <option value="REVIEW">Failure review</option>
        </select>

        <button type="submit" className="queue-filter-button">
          <FaFilter />
          Filter{activeFilterCount ? ` (${activeFilterCount})` : ""}
        </button>

        <button
          type="button"
          className="queue-reset-button"
          onClick={resetFilters}
        >
          Reset
        </button>
      </form>

      <div className="queue-card return-queue-card">
        <div className="queue-card-head">
          <div>
            <strong>{returns.length}</strong>
            <span> active customer returns</span>
          </div>
          <span className="queue-live-indicator">
            <i /> Reverse logistics
          </span>
        </div>
        {returns.length === 0 ? (
          <div className="queue-empty">
            <FaTruck />
            <strong>No active returns</strong>
            <span>
              Return requests will appear here as soon as customers request
              them.
            </span>
          </div>
        ) : (
          <div className="queue-table-wrap">
            <table className="queue-table">
              <thead>
                <tr>
                  <th>Return</th>
                  <th>Pickup from customer</th>
                  <th>Supplier destination</th>
                  <th>Stage</th>
                  <th>Courier shipment</th>
                  <th>Agent</th>
                  <th>Last update</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {returns.map((item) => (
                  <tr key={`return-${item.id}`}>
                    <td>
                      <Link
                        to={`/returns/${item.id}`}
                        className="queue-order-link"
                      >
                        Return #{item.id}
                      </Link>
                      <span className="queue-muted">
                        Order #{item.order_id}
                      </span>
                    </td>
                    <td>
                      <strong>{item.customer?.name || "—"}</strong>
                      <span className="queue-muted">
                        {item.customer_pickup_address?.city || ""}
                      </span>
                    </td>
                    <td>
                      <strong>
                        {item.delivery?.supplier?.business_name ||
                          item.delivery?.supplier?.name ||
                          "Supplier"}
                      </strong>
                      <span className="queue-muted">
                        {item.delivery?.supplier?.city ||
                          "Address not configured"}
                      </span>
                    </td>
                    <td>
                      <span className="queue-status amber">
                        {item.delivery?.stage_label || item.status}
                      </span>
                      <span className="queue-pending">
                        {item.delivery?.pending_action || "No pending action"}
                      </span>
                    </td>
                    <td>
                      <strong>
                        {item.delivery?.agent?.name || "Unassigned"}
                      </strong>
                      <span className="queue-muted">
                        {item.delivery?.agent?.phone || ""}
                      </span>
                    </td>
                    <td className="queue-time">
                      {formatDate(
                        item.delivery?.updated_at ||
                          item.updated_at ||
                          item.created_at,
                      )}
                    </td>
                    <td>
                      <Link to={`/returns/${item.id}`} className="queue-view">
                        Open <FaArrowRight />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="queue-card">
        <div className="queue-card-head">
          <div>
            <strong>{queue.length}</strong>
            <span> matching operational records</span>
          </div>
          <span className="queue-live-indicator">
            <i /> Auto-refresh 12s
          </span>
        </div>

        {loading ? (
          <div className="queue-empty">
            <FaTruck />
            <strong>Loading delivery queue…</strong>
            <span>Fetching current logistics state from the backend.</span>
          </div>
        ) : queue.length === 0 ? (
          <div className="queue-empty">
            <FaTruck />
            <strong>No matching shipments</strong>
            <span>Try another filter or wait for a supplier handoff.</span>
          </div>
        ) : (
          <div className="queue-table-wrap">
            <table className="queue-table">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Recipient</th>
                  <th>Destination</th>
                  <th>Stage</th>
                  <th>Agent</th>
                  <th>Last update</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.order_id}>
                    <td>
                      <Link
                        to={`/orders/${item.order_id}`}
                        className="queue-order-link"
                      >
                        #{item.order_id}
                      </Link>
                      <span className="queue-muted">{item.order_status}</span>
                    </td>
                    <td>
                      <strong>{item.customer?.name || "—"}</strong>
                      <span className="queue-muted">
                        {item.customer?.phone || ""}
                      </span>
                    </td>
                    <td>
                      <strong>{item.destination?.city || "—"}</strong>
                      <span className="queue-muted">
                        {item.destination?.state || ""}
                        {item.destination?.postal_code
                          ? ` · ${item.destination.postal_code}`
                          : ""}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`queue-status ${statusClass(item.stage)}`}
                      >
                        {item.stage_label}
                      </span>
                      <span className="queue-pending">
                        {item.pending_action || "No pending action"}
                      </span>
                    </td>
                    <td>
                      {item.shipments?.length ? (
                        item.shipments.map((shipment) => (
                          <span className="queue-muted" key={shipment.id}>
                            {shipment.courier_name || "Courier pending"}
                            {shipment.awb_code
                              ? ` · AWB ${shipment.awb_code}`
                              : ""}
                            <br />
                            {String(shipment.status || "PENDING").replaceAll(
                              "_",
                              " ",
                            )}
                          </span>
                        ))
                      ) : (
                        <span className="queue-muted">
                          Provisioning pending
                        </span>
                      )}
                    </td>
                    <td>
                      <strong>{item.agent?.name || "Unassigned"}</strong>
                      <span className="queue-muted">
                        {item.agent?.phone || ""}
                      </span>
                    </td>
                    <td className="queue-time">
                      {formatDate(item.updated_at || item.created_at)}
                    </td>
                    <td>
                      <Link
                        to={`/orders/${item.order_id}`}
                        className="queue-view"
                      >
                        Open <FaArrowRight />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
