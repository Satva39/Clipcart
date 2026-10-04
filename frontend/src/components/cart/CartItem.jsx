import { useState } from "react";
import { FiHeart, FiMinus, FiPlus, FiTrash2 } from "react-icons/fi";
import { Link } from "react-router-dom";
import { useCart } from "../../context/CartContext";
import { formatCurrency } from "../../utils/formatters";

const SAVED_KEY = "clipcart_saved_for_later";
function getSaved() {
  try {
    const data = localStorage.getItem(SAVED_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}
function save(items) {
  localStorage.setItem(SAVED_KEY, JSON.stringify(items));
}

export default function CartItem({ item }) {
  const { updateQuantity, removeFromCart } = useCart();
  const [saving, setSaving] = useState(false);

  function saveForLater() {
    setSaving(true);
    const next = [
      item,
      ...getSaved().filter((saved) => saved.id !== item.id),
    ].slice(0, 12);
    save(next);
    removeFromCart(item.product_id, item.variant_id).finally(() =>
      setSaving(false),
    );
  }

  return (
    <article className="cc-cart-item">
      <Link className="cc-cart-image" to={`/product/${item.product_id}`}>
        <img src={item.image || "/placeholder.png"} alt={item.name} />
      </Link>
      <div className="cc-cart-item-main">
        <div className="cc-product-meta">
          {item.brand ? <span>{item.brand}</span> : null}
          {item.category ? <span>{item.category}</span> : null}
        </div>
        <Link to={`/product/${item.product_id}`} className="cc-cart-title">
          {item.name}
        </Link>
        {item.variant_value ? (
          <p className="cc-cart-variant">Variant: {item.variant_value}</p>
        ) : null}
        <p
          className={
            Number(item.stock) > 0 ? "cc-stock-text in" : "cc-stock-text out"
          }
        >
          {Number(item.stock) > 0 ? "In stock" : "Unavailable"}
        </p>
        <div className="cc-cart-price">
          <strong>{formatCurrency(item.price)}</strong>
          {item.compare_price ? (
            <span>{formatCurrency(item.compare_price)}</span>
          ) : null}
        </div>

        <div className="cc-cart-actions">
          <div className="cc-cart-quantity">
            <button
              className="cc-cart-quantity-btn"
              type="button"
              onClick={() =>
                updateQuantity(
                  item.product_id,
                  item.quantity - 1,
                  item.variant_id,
                )
              }
              aria-label="Decrease quantity"
            >
              <FiMinus />
            </button>
            <span className="cc-cart-quantity-value">{item.quantity}</span>
            <button
              className="cc-cart-quantity-btn"
              type="button"
              disabled={Number(item.quantity) >= Number(item.stock)}
              onClick={() =>
                updateQuantity(
                  item.product_id,
                  item.quantity + 1,
                  item.variant_id,
                )
              }
              aria-label="Increase quantity"
            >
              <FiPlus />
            </button>
          </div>
          <button
            type="button"
            className="cc-link-button"
            onClick={saveForLater}
            disabled={saving}
          >
            <FiHeart /> {saving ? "Saving…" : "Save for later"}
          </button>
          <button
            type="button"
            className="cc-link-button danger"
            onClick={() => removeFromCart(item.product_id, item.variant_id)}
          >
            <FiTrash2 /> Remove
          </button>
        </div>
      </div>
      <div className="cc-cart-total">
        {formatCurrency(Number(item.price) * Number(item.quantity))}
      </div>
    </article>
  );
}
