import { FiShield } from "react-icons/fi";
import Container from "../../components/common/Container";
import CartList from "../../components/cart/CartList";
import CartSummary from "../../components/cart/CartSummary";
import SavedForLater from "../../components/cart/SavedForLater";

export default function CartPage() {
  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-page-heading">
          <div>
            <span className="cc-eyebrow">Your shopping cart</span>
            <h1>Cart</h1>
            <p>Review quantities, variants and totals before checkout.</p>
          </div>
          <span className="cc-secure-note">
            <FiShield /> Secure checkout
          </span>
        </div>
        <div className="cc-cart-layout">
          <CartList />
          <CartSummary />
        </div>
      </Container>
      <SavedForLater />
    </div>
  );
}
