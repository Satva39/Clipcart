import { Link } from "react-router-dom";
import { FiArrowRight } from "react-icons/fi";
import { useCart } from "../../context/CartContext";
import { formatCurrency } from "../../utils/formatters";

export default function CartSummary() {
  const { cartItems, cartSubtotal } = useCart();
  if (!cartItems.length) return null;
  return (
    <aside className="cc-summary-card">
      <h2>Order summary</h2>
      <div className="cc-summary-lines">
        <div>
          <span>
            Items (
            {cartItems.reduce(
              (sum, item) => sum + Number(item.quantity || 0),
              0,
            )}
            )
          </span>
          <strong>{formatCurrency(cartSubtotal)}</strong>
        </div>
        <div>
          <span>Delivery</span>
          <span>Calculated at checkout</span>
        </div>
      </div>
      <div className="cc-summary-total">
        <span>Subtotal</span>
        <strong>{formatCurrency(cartSubtotal)}</strong>
      </div>
      <Link to="/checkout" className="cc-btn primary full">
        Proceed to checkout <FiArrowRight />
      </Link>
      <p className="cc-summary-note">
        Final charges are calculated by the backend checkout service.
      </p>
    </aside>
  );
}
