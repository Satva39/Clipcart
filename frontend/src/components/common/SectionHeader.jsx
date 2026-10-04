import { Link } from "react-router-dom";

export default function SectionHeader({
  title,
  description,
  to,
  action = "View all",
}) {
  return (
    <div className="cc-section-header">
      <div>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {to ? (
        <Link className="cc-text-link" to={to}>
          {action} →
        </Link>
      ) : null}
    </div>
  );
}
