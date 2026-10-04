import { FiZap } from "react-icons/fi";
import { Link } from "react-router-dom";

export default function FlashDeals({ count = 0 }) {
  if (!count) return null;
  return (
    <div className="cc-deal-strip">
      <div className="cc-container cc-deal-strip-inner">
        <div>
          <span className="cc-deal-label">
            <FiZap /> Live deals
          </span>
          <strong>Save on products with an active compare price.</strong>
        </div>
        <Link to="/products?discount=true">See deals →</Link>
      </div>
    </div>
  );
}
