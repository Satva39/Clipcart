export default function ProductSkeleton({ count = 4 }) {
  return (
    <div className="cc-product-grid">
      {Array.from({ length: count }).map((_, index) => (
        <div
          className="cc-product-card cc-product-skeleton"
          key={index}
          aria-hidden="true"
        >
          <div className="cc-skeleton cc-skeleton-image" />
          <div className="cc-skeleton cc-skeleton-line wide" />
          <div className="cc-skeleton cc-skeleton-line" />
          <div className="cc-skeleton cc-skeleton-line short" />
          <div className="cc-skeleton cc-skeleton-button" />
        </div>
      ))}
    </div>
  );
}
