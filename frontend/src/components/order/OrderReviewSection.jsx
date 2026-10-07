import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FaCheckCircle, FaImage, FaStar, FaTimes } from "react-icons/fa";
import { FiUpload } from "react-icons/fi";
import { getMyReviews, createReview } from "../../services/reviewService";
import { getApiMessage } from "../../utils/apiError";

function Stars({ value, onChange }) {
  return (
    <div
      className="cc-order-review-stars"
      aria-label={`Rating ${value} out of 5`}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={star <= value ? "active" : ""}
          onClick={() => onChange?.(star)}
          disabled={!onChange}
          aria-label={`${star} star${star === 1 ? "" : "s"}`}
        >
          <FaStar />
        </button>
      ))}
    </div>
  );
}

function ReviewMedia({ media = [] }) {
  if (!media.length) return null;
  return (
    <div className="cc-order-review-media-grid">
      {media.map((item) =>
        item.type === "video" ? (
          <video
            key={item.id}
            className="cc-order-review-media"
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
            className="cc-order-review-media-link"
          >
            <img
              className="cc-order-review-media"
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

export default function OrderReviewSection({ order }) {
  const client = useQueryClient();
  const [selectedItemId, setSelectedItemId] = useState("");
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [review, setReview] = useState("");
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reviewsQuery = useQuery({
    queryKey: ["reviews", "mine", "order", order.id],
    queryFn: () => getMyReviews(null, order.id),
    enabled: Boolean(order?.id),
  });

  const reviews = Array.isArray(reviewsQuery.data) ? reviewsQuery.data : [];
  const reviewByItem = useMemo(
    () => new Map(reviews.map((item) => [Number(item.order_item_id), item])),
    [reviews],
  );
  const availableItems = (order.items || []).filter(
    (item) => !reviewByItem.has(Number(item.id)),
  );

  useEffect(() => {
    if (!selectedItemId && availableItems.length === 1) {
      setSelectedItemId(String(availableItems[0].id));
    } else if (
      selectedItemId &&
      !availableItems.some((item) => String(item.id) === selectedItemId)
    ) {
      setSelectedItemId("");
    }
  }, [availableItems, selectedItemId]);

  function resetForm() {
    setRating(0);
    setTitle("");
    setReview("");
    setFiles([]);
  }

  function handleFiles(event) {
    const selected = Array.from(event.target.files || []);
    const valid = selected.filter((file) =>
      [
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/mp4",
        "video/webm",
        "video/quicktime",
      ].includes(file.type),
    );
    if (valid.length !== selected.length) {
      setMessage("Use JPG, PNG or WebP images, or MP4, WebM or MOV videos.");
    } else if (valid.length > 6) {
      setMessage("You can upload up to 6 photos or videos per review.");
    } else if (
      valid.reduce((sum, file) => sum + file.size, 0) >
      60 * 1024 * 1024
    ) {
      setMessage("The total review media upload must be 60 MB or smaller.");
    } else {
      setMessage("");
      setFiles(valid);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (!selectedItemId)
      return setMessage("Select the item you want to review.");
    if (!rating) return setMessage("Please select a star rating.");
    if (!review.trim()) return setMessage("Please write your review.");

    const item = (order.items || []).find(
      (entry) => String(entry.id) === selectedItemId,
    );
    if (!item) return;

    setSubmitting(true);
    setMessage("");
    try {
      await createReview(
        {
          product_id: Number(item.product_id),
          order_item_id: Number(item.id),
          rating,
          title,
          review,
        },
        files,
      );
      setMessage("Review submitted. It will appear publicly after moderation.");
      resetForm();
      setSelectedItemId("");
      await client.invalidateQueries({
        queryKey: ["reviews", "mine", "order", order.id],
      });
      await client.invalidateQueries({
        queryKey: ["reviews", item.product_id],
      });
    } catch (error) {
      setMessage(getApiMessage(error, "Unable to submit your review."));
    } finally {
      setSubmitting(false);
    }
  }

  if (order.status !== "DELIVERED") return null;

  return (
    <section className="cc-order-review-section">
      <div className="cc-order-review-heading">
        <div>
          <span className="cc-order-review-eyebrow">
            Your experience matters
          </span>
          <h3>Review your order</h3>
          <p>
            Share your rating, feedback and real photos or videos of the
            delivered product.
          </p>
        </div>
      </div>

      {reviews.length ? (
        <div className="cc-order-review-submitted-list">
          {reviews.map((item) => (
            <article key={item.id} className="cc-order-review-submitted">
              <div className="cc-order-review-submitted-top">
                <div>
                  <strong>
                    {(order.items || []).find(
                      (entry) =>
                        Number(entry.id) === Number(item.order_item_id),
                    )?.product_name || "Purchased item"}
                  </strong>
                  <span>
                    <FaCheckCircle /> Review submitted
                  </span>
                </div>
                <div className="cc-order-review-score">
                  <Stars value={Number(item.rating || 0)} onChange={() => {}} />
                </div>
              </div>
              {item.title ? (
                <strong className="cc-order-review-submitted-title">
                  {item.title}
                </strong>
              ) : null}
              <p>{item.review}</p>
              <ReviewMedia media={item.media} />
            </article>
          ))}
        </div>
      ) : null}

      {availableItems.length ? (
        <form className="cc-order-review-form" onSubmit={submit}>
          <label>
            Item to review
            <select
              value={selectedItemId}
              onChange={(event) => setSelectedItemId(event.target.value)}
              className="cc-review-select"
            >
              <option value="">Select a delivered item</option>
              {availableItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.product_name}
                  {item.variant_value ? ` · ${item.variant_value}` : ""}
                </option>
              ))}
            </select>
          </label>

          <div>
            <p className="cc-review-field-label">Your rating</p>
            <Stars value={rating} onChange={setRating} />
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
            rows={4}
            required
            placeholder="Tell us about your experience…"
            className="cc-review-textarea"
          />

          <label className="cc-order-review-upload">
            <span>
              <FiUpload /> Add photos or videos
            </span>
            <small>Up to 6 files · images and short videos</small>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"
              multiple
              onChange={handleFiles}
            />
          </label>

          {files.length ? (
            <div className="cc-order-review-file-list">
              {files.map((file) => (
                <span key={`${file.name}-${file.size}`}>
                  <FaImage /> {file.name}
                  <button
                    type="button"
                    aria-label={`Remove ${file.name}`}
                    onClick={() =>
                      setFiles((current) =>
                        current.filter((entry) => entry !== file),
                      )
                    }
                  >
                    <FaTimes />
                  </button>
                </span>
              ))}
            </div>
          ) : null}

          <button
            type="submit"
            className="cc-btn primary full"
            disabled={submitting}
          >
            {submitting ? "Submitting…" : "Submit review"}
          </button>
          {message ? (
            <p className="cc-order-review-message" role="status">
              {message}
            </p>
          ) : null}
        </form>
      ) : reviews.length ? (
        <p className="cc-order-review-complete">
          You have reviewed every item in this order. Thank you for your
          feedback.
        </p>
      ) : (
        <p className="cc-order-review-complete">
          There are no eligible items available for review.
        </p>
      )}
    </section>
  );
}
