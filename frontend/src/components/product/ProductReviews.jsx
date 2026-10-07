import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FaCheckCircle, FaRegStar, FaStar } from "react-icons/fa";
import { useAuth } from "../../context/AuthContext";
import {
  createReview,
  deleteReview,
  getMyReviews,
  getProductReviews,
  updateReview,
} from "../../services/reviewService";
import { getReviewableItems } from "../../services/orderService";
import { getApiMessage } from "../../utils/apiError";

function StarRating({ value, onChange, size = "default" }) {
  return (
    <div
      className={`cc-review-stars ${size}`.trim()}
      aria-label={`Rating ${value} out of 5`}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange?.(star)}
          disabled={!onChange}
          className={star <= value ? "filled" : "empty"}
          aria-label={`${star} star${star === 1 ? "" : "s"}`}
        >
          {star <= value ? <FaStar /> : <FaRegStar />}
        </button>
      ))}
    </div>
  );
}

function ReviewMediaGrid({ media = [] }) {
  if (!media.length) return null;
  return (
    <div className="cc-review-media-grid">
      {media.map((item) =>
        item.type === "video" ? (
          <video
            key={item.id}
            className="cc-review-media"
            src={item.url}
            controls
            preload="metadata"
          />
        ) : (
          <a
            key={item.id}
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="cc-review-media-link"
          >
            <img
              className="cc-review-media"
              src={item.url}
              alt="Customer review"
              loading="lazy"
            />
          </a>
        ),
      )}
    </div>
  );
}

function ReviewCard({ review, editable, onEdit, onDelete }) {
  return (
    <article className="cc-review-card">
      <div className="cc-review-card-top">
        <div>
          <h4>{review.title || "Customer Review"}</h4>
          <p className="cc-review-author">
            {review.customer || "Customer"}
            {review.approved === false ? " · Pending moderation" : ""}
          </p>
        </div>
        <StarRating value={Number(review.rating || 0)} size="small" />
      </div>
      <p className="cc-review-copy">{review.review}</p>
      <ReviewMediaGrid media={review.media} />
      {review.verified_purchase ? (
        <div className="cc-review-verified">
          <FaCheckCircle /> Verified Purchase
        </div>
      ) : null}
      {editable ? (
        <div className="cc-review-actions">
          <button
            type="button"
            className="cc-btn secondary"
            onClick={() => onEdit(review)}
          >
            Edit
          </button>
          <button
            type="button"
            className="cc-btn secondary danger"
            onClick={() => onDelete(review)}
          >
            Delete
          </button>
        </div>
      ) : null}
    </article>
  );
}

export default function ProductReviews({ productId }) {
  const { user } = useAuth();
  const client = useQueryClient();
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [review, setReview] = useState("");
  const [orderItemId, setOrderItemId] = useState("");
  const [editingReviewId, setEditingReviewId] = useState(null);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reviewsQuery = useQuery({
    queryKey: ["reviews", productId],
    queryFn: () => getProductReviews(productId),
    enabled: Boolean(productId),
  });
  const eligibleQuery = useQuery({
    queryKey: ["orders", "reviewable", productId],
    queryFn: () => getReviewableItems(productId),
    enabled: Boolean(user && productId),
  });
  const mineQuery = useQuery({
    queryKey: ["reviews", "mine", productId],
    queryFn: () => getMyReviews(productId),
    enabled: Boolean(user && productId),
  });

  const data = reviewsQuery.data || { reviews: [], summary: {} };
  const reviews = Array.isArray(data.reviews) ? data.reviews : [];
  const summary = data.summary || {};
  const mine = useMemo(
    () => (Array.isArray(mineQuery.data) ? mineQuery.data : []),
    [mineQuery.data],
  );
  const pendingMine = useMemo(
    () => mine.filter((item) => !item.approved),
    [mine],
  );
  const eligibleItems = useMemo(
    () => (Array.isArray(eligibleQuery.data) ? eligibleQuery.data : []),
    [eligibleQuery.data],
  );

  const availableItems = useMemo(
    () =>
      eligibleItems.filter(
        (item) =>
          !mine.some(
            (entry) =>
              Number(entry.order_item_id) === Number(item.order_item_id),
          ),
      ),
    [eligibleItems, mine],
  );

  function resetForm() {
    setRating(0);
    setTitle("");
    setReview("");
    setOrderItemId("");
    setEditingReviewId(null);
  }

  function beginEdit(item) {
    setEditingReviewId(item.id);
    setRating(Number(item.rating || 0));
    setTitle(item.title || "");
    setReview(item.review || "");
    setMessage("");
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }

  async function handleDelete(item) {
    if (!window.confirm("Delete this review?")) return;
    try {
      await deleteReview(item.id);
      setMessage("Review deleted.");
      await Promise.all([
        client.invalidateQueries({ queryKey: ["reviews", productId] }),
        client.invalidateQueries({ queryKey: ["reviews", "mine", productId] }),
      ]);
    } catch (error) {
      setMessage(getApiMessage(error, "Unable to delete this review."));
    }
  }

  const selectedOrderItemId =
    orderItemId ||
    (availableItems.length === 1
      ? String(availableItems[0].order_item_id)
      : "");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!user) return;
    if (!rating) {
      setMessage("Please select a star rating.");
      return;
    }
    if (!review.trim()) {
      setMessage("Please write your review.");
      return;
    }
    if (!editingReviewId && !selectedOrderItemId) {
      setMessage("Only delivered purchases can be reviewed.");
      return;
    }

    setSubmitting(true);
    setMessage("");
    try {
      if (editingReviewId) {
        await updateReview(editingReviewId, { rating, title, review });
        setMessage("Review updated and sent back for moderation.");
      } else {
        await createReview({
          product_id: Number(productId),
          order_item_id: Number(selectedOrderItemId),
          rating,
          title,
          review,
        });
        setMessage("Review submitted for moderation.");
      }
      resetForm();
      await Promise.all([
        client.invalidateQueries({ queryKey: ["reviews", productId] }),
        client.invalidateQueries({ queryKey: ["reviews", "mine", productId] }),
        client.invalidateQueries({
          queryKey: ["orders", "reviewable", productId],
        }),
      ]);
    } catch (error) {
      setMessage(getApiMessage(error, "Unable to submit the review."));
    } finally {
      setSubmitting(false);
    }
  }

  const distribution = summary.distribution || {};
  return (
    <section className="cc-reviews-section">
      <div className="cc-reviews-heading">
        <div>
          <h2>Customer Reviews</h2>
          <p>Approved feedback from Clipcart customers.</p>
        </div>
        <span className="cc-reviews-count">
          {Number(summary.count || 0)} review
          {Number(summary.count || 0) === 1 ? "" : "s"}
        </span>
      </div>

      <div className="cc-review-summary">
        <div className="cc-review-average">
          <div className="cc-review-average-number">
            {Number(summary.average || 0).toFixed(1)}
          </div>
          <div className="cc-review-average-stars">
            <StarRating
              value={Math.round(Number(summary.average || 0))}
              size="text-lg"
            />
          </div>
          <p className="cc-review-average-count">
            {Number(summary.count || 0)} ratings
          </p>
        </div>
        <div className="cc-review-distribution">
          {[5, 4, 3, 2, 1].map((star) => {
            const count = Number(distribution[star] || 0);
            const total = Number(summary.count || 0);
            const percentage = total ? (count / total) * 100 : 0;
            return (
              <div key={star} className="cc-review-distribution-row">
                <span className="cc-review-distribution-label">{star} ★</span>
                <div className="cc-review-bar">
                  <div
                    className="cc-review-bar-fill"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="cc-review-distribution-count">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {Number(summary.count || 0) === 0 && pendingMine.length ? (
        <p className="cc-review-moderation-note">
          {pendingMine.length} review
          {pendingMine.length === 1 ? " is" : "s are"} waiting for moderation
          and are not included in the public rating yet.
        </p>
      ) : null}

      {user ? (
        <div className="cc-review-form-card">
          <div className="cc-review-form-head">
            <div>
              <h3>{editingReviewId ? "Edit your review" : "Write a review"}</h3>
              <p className="cc-review-author">
                Reviews require a delivered purchase and are checked by
                moderation.
              </p>
            </div>
            {editingReviewId ? (
              <button
                type="button"
                className="cc-btn secondary"
                onClick={resetForm}
              >
                Cancel edit
              </button>
            ) : null}
          </div>

          {!editingReviewId && eligibleQuery.isLoading ? (
            <p className="cc-review-info">Checking eligible purchases…</p>
          ) : null}
          {!editingReviewId &&
          !eligibleQuery.isLoading &&
          availableItems.length === 0 ? (
            <p className="cc-review-empty">
              There is no delivered purchase of this product available for a new
              review.
            </p>
          ) : null}

          {editingReviewId || availableItems.length > 0 ? (
            <form onSubmit={handleSubmit} className="cc-review-form">
              {!editingReviewId ? (
                <label>
                  Purchased item
                  <select
                    value={selectedOrderItemId}
                    onChange={(event) => setOrderItemId(event.target.value)}
                    className="cc-review-select"
                  >
                    <option value="">Select a delivered purchase</option>
                    {availableItems.map((item) => (
                      <option
                        key={item.order_item_id}
                        value={item.order_item_id}
                      >
                        Order #{item.order_id} · {item.product_name}
                        {item.variant_value ? ` · ${item.variant_value}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              <div>
                <p className="cc-review-field-label">Your rating</p>
                <StarRating value={rating} onChange={setRating} size="large" />
              </div>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={255}
                placeholder="Review title (optional)"
                className="cc-review-input"
              />
              <textarea
                value={review}
                onChange={(event) => setReview(event.target.value)}
                maxLength={5000}
                rows={5}
                required
                placeholder="What did you like or dislike?"
                className="cc-review-textarea"
              />
              <button
                type="submit"
                disabled={submitting}
                className="cc-btn primary"
              >
                {submitting
                  ? "Saving…"
                  : editingReviewId
                    ? "Update review"
                    : "Submit review"}
              </button>
              {message ? (
                <p className="cc-review-status" role="status">
                  {message}
                </p>
              ) : null}
            </form>
          ) : null}
        </div>
      ) : null}

      {pendingMine.length ? (
        <div className="cc-review-pending-list">
          <div className="cc-review-pending-head">
            <div>
              <h3>My pending reviews</h3>
              <p>
                These reviews are awaiting moderation and can be edited or
                deleted while pending.
              </p>
            </div>
          </div>
          {pendingMine.map((item) => (
            <ReviewCard
              key={item.id}
              review={item}
              editable
              onEdit={beginEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : null}

      <div className="cc-review-list">
        {reviewsQuery.isLoading ? (
          <div className="cc-review-loading">Loading reviews…</div>
        ) : null}
        {!reviewsQuery.isLoading && reviews.length === 0 ? (
          <div className="cc-review-empty-panel">
            <FaStar className="cc-review-empty-icon" />
            <h3>No approved reviews yet</h3>
            <p>Verified customer reviews will appear here after moderation.</p>
          </div>
        ) : null}
        {reviews.map((item) => (
          <ReviewCard
            key={item.id}
            review={item}
            editable={false}
            onEdit={() => {}}
            onDelete={() => {}}
          />
        ))}
      </div>
    </section>
  );
}
