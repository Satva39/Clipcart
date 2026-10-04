import { useState } from "react";
import { FiShoppingCart, FiTrash2 } from "react-icons/fi";
import { Link } from "react-router-dom";
import { useCart } from "../../context/CartContext";
import { getApiMessage } from "../../utils/apiError";
import { formatCurrency, getProductImage } from "../../utils/formatters";

const KEY = "clipcart_saved_for_later";
function read() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
function write(items) {
  localStorage.setItem(KEY, JSON.stringify(items));
}

export default function SavedForLater() {
  const [items, setItems] = useState(read);
  const [message, setMessage] = useState("");
  const { addToCart } = useCart();

  if (!items.length) return null;

  async function move(item) {
    try {
      await addToCart(item, item.quantity || 1);
      const next = items.filter((saved) => saved.id !== item.id);
      setItems(next);
      write(next);
      setMessage("Moved to cart");
    } catch (error) {
      setMessage(getApiMessage(error, "Couldn't move the item to your cart."));
    }
  }

  function remove(item) {
    const next = items.filter((saved) => saved.id !== item.id);
    setItems(next);
    write(next);
  }

  return (
    <section className="cc-section compact-section">
      <div className="cc-container">
        <div className="cc-section-header">
          <div>
            <h2>Saved for later</h2>
            <p>Items kept on this device for another shopping session.</p>
          </div>
        </div>
        <div className="cc-saved-grid">
          {items.map((item) => (
            <article key={item.id} className="cc-saved-card">
              <Link to={`/product/${item.product_id}`}>
                <img
                  src={getProductImage(item)}
                  alt={item.name}
                  loading="lazy"
                  decoding="async"
                />
              </Link>
              <div>
                <Link
                  to={`/product/${item.product_id}`}
                  className="cc-cart-title"
                >
                  {item.name}
                </Link>
                <strong>{formatCurrency(item.price)}</strong>
                <div className="cc-inline-actions">
                  <button type="button" onClick={() => move(item)}>
                    <FiShoppingCart /> Move to cart
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => remove(item)}
                  >
                    <FiTrash2 /> Remove
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
        {message ? <p className="cc-inline-message">{message}</p> : null}
      </div>
    </section>
  );
}
