export function LoadingState({ label = "Loading...", compact = false }) {
  return (
    <div
      className={`cc-loading-state${compact ? " compact" : ""}`}
      role="status"
      aria-live="polite"
    >
      <span className="cc-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({
  message = "We couldn't load this right now.",
  onRetry,
}) {
  return (
    <div className="cc-state-panel cc-state-error" role="alert">
      <strong>Something went wrong</strong>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="cc-btn secondary" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ icon = "○", title, message, action }) {
  return (
    <div className="cc-state-panel">
      <div className="cc-empty-icon" aria-hidden="true">
        {icon}
      </div>
      <h3>{title}</h3>
      <p>{message}</p>
      {action ? action : null}
    </div>
  );
}
