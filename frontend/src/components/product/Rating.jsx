export default function Rating({
  value = 0,
  count,
  showValue = true,
  size = "sm",
}) {
  const numeric = Math.max(0, Math.min(5, Number(value || 0)));
  const rounded = Math.round(numeric);

  return (
    <span
      className={`cc-rating ${size}`}
      aria-label={`${numeric.toFixed(1)} out of 5 stars`}
    >
      <span className="cc-stars" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((star) => (
          <span key={star} className={star <= rounded ? "filled" : ""}>
            ★
          </span>
        ))}
      </span>
      {showValue ? (
        <span className="cc-rating-number">{numeric.toFixed(1)}</span>
      ) : null}
      {count !== undefined ? (
        <span className="cc-rating-count">({count})</span>
      ) : null}
    </span>
  );
}
