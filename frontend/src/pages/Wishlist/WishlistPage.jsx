import { useEffect, useState } from "react";
import { FiHeart, FiShoppingCart, FiTrash2 } from "react-icons/fi";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";
import { getApiMessage } from "../../utils/apiError";
import { formatCurrency, getProductImage } from "../../utils/formatters";
import Container from "../../components/common/Container";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/common/AsyncState";

export default function WishlistPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { items, loading, toggle } = useWishlist();
  const { addToCart } = useCart();
  const [actionId, setActionId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user && !loading)
      navigate(`/login?redirect=${encodeURIComponent("/wishlist")}`, {
        replace: true,
      });
  }, [user, loading, navigate]);

  if (!user || loading)
    return (
      <div className="cc-page-shell">
        <Container>
          {loading ? <LoadingState label="Loading wishlist…" /> : null}
        </Container>
      </div>
    );
  if (error)
    return (
      <div className="cc-page-shell">
        <Container>
          <ErrorState message={error} />
        </Container>
      </div>
    );

  async function remove(item) {
    setActionId(item.id);
    setError("");
    try {
      await toggle(item);
    } catch (err) {
      setError(getApiMessage(err, "Couldn't remove this item."));
    } finally {
      setActionId(null);
    }
  }

  async function add(item) {
    setActionId(item.id);
    setError("");
    try {
      await addToCart(item, 1);
    } catch (err) {
      setError(getApiMessage(err, "Couldn't add this item to your cart."));
    } finally {
      setActionId(null);
    }
  }

  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-page-heading">
          <div>
            <span className="cc-eyebrow">Saved products</span>
            <h1>Wishlist</h1>
            <p>
              {items.length} saved product{items.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        {!items.length ? (
          <EmptyState
            icon={<FiHeart />}
            title="Your wishlist is empty"
            message="Save products you want to compare or buy later."
            action={
              <Link className="cc-btn primary" to="/products">
                Browse products
              </Link>
            }
          />
        ) : (
          <div className="cc-wishlist-grid">
            {items.map((item) => {
              const available = Number(item.stock || 0) > 0;
              return (
                <article key={item.id} className="cc-wishlist-card">
                  <Link
                    className="cc-wishlist-image"
                    to={`/product/${item.id}`}
                  >
                    <img
                      src={getProductImage(item)}
                      alt={item.name}
                      loading="lazy"
                      decoding="async"
                    />
                  </Link>
                  <div className="cc-wishlist-body">
                    <div className="cc-product-meta">
                      {item.brand ? (
                        <span>{item.brand?.name || item.brand}</span>
                      ) : null}
                      {item.category ? (
                        <span>{item.category?.name || item.category}</span>
                      ) : null}
                    </div>
                    <Link to={`/product/${item.id}`} className="cc-cart-title">
                      {item.name}
                    </Link>
                    <div className="cc-wishlist-price">
                      <strong>{formatCurrency(item.price)}</strong>
                      {item.compare_price ? (
                        <span>{formatCurrency(item.compare_price)}</span>
                      ) : null}
                    </div>
                    <p
                      className={
                        available ? "cc-stock-text in" : "cc-stock-text out"
                      }
                    >
                      {available ? "In stock" : "Currently unavailable"}
                    </p>
                    <div className="cc-inline-actions">
                      <button
                        type="button"
                        className="cc-btn primary"
                        disabled={!available || actionId === item.id}
                        onClick={() => add(item)}
                      >
                        <FiShoppingCart />{" "}
                        {actionId === item.id ? "Working…" : "Add to cart"}
                      </button>
                      <button
                        type="button"
                        className="cc-link-button danger"
                        disabled={actionId === item.id}
                        onClick={() => remove(item)}
                      >
                        <FiTrash2 /> Remove
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </Container>
    </div>
  );
}
