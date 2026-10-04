import { FiShoppingBag, FiTrash2 } from "react-icons/fi";
import { useCart } from "../../context/CartContext";
import CartItem from "./CartItem";
import { EmptyState } from "../common/AsyncState";

export default function CartList() {
  const { cartItems, clearCart, cartLoading } = useCart();
  if (cartLoading)
    return (
      <div className="cc-loading-state">
        <span className="cc-spinner" /> Syncing your cart…
      </div>
    );
  if (!cartItems.length)
    return (
      <EmptyState
        icon={<FiShoppingBag />}
        title="Your cart is empty"
        message="Add products from the catalog and they will appear here."
      />
    );
  return (
    <div className="cc-cart-list-wrap">
      <div className="cc-cart-list-head">
        <strong>
          {cartItems.length} product{cartItems.length !== 1 ? "s" : ""}
        </strong>
        <button
          type="button"
          className="cc-link-button danger"
          onClick={clearCart}
        >
          <FiTrash2 /> Clear cart
        </button>
      </div>
      <div className="cc-cart-list">
        {cartItems.map((item) => (
          <CartItem key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}
