import { memo, useState } from "react";
import { FiHeart, FiShoppingCart } from "react-icons/fi";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../../context/CartContext";
import { useAuth } from "../../context/AuthContext";
import { useWishlist } from "../../context/WishlistContext";
import { getApiMessage } from "../../utils/apiError";
import {
  getCategoryName,
  getBrandName,
  getProductImage,
} from "../../utils/formatters";
import Price from "./Price";
import Rating from "./Rating";

function ProductCard({ product, compact = false }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToCart } = useCart();
  const { itemIds, toggle } = useWishlist();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const image = getProductImage(product);
  const category = getCategoryName(product.category);
  const brand = getBrandName(product.brand);
  const inStock = Number(product.stock || 0) > 0;
  const wishlisted = itemIds.has(Number(product.id));

  async function handleCart(event) {
    event.preventDefault();
    event.stopPropagation();
    if (!inStock || busy) return;
    setBusy(true);
    setNotice("");
    try {
      await addToCart(product, 1);
      setNotice("Added to cart");
    } catch (error) {
      setNotice(
        getApiMessage(error, "Couldn't add this product to your cart."),
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleWishlist(event) {
    event.preventDefault();
    event.stopPropagation();
    if (!user) {
      navigate(
        `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`,
      );
      return;
    }
    setNotice("");
    try {
      await toggle(product);
      setNotice(wishlisted ? "Removed from wishlist" : "Saved to wishlist");
    } catch (error) {
      setNotice(getApiMessage(error, "Couldn't update your wishlist."));
    }
  }

  return (
    <article className={`cc-product-card${compact ? " compact" : ""}`}>
      <div className="cc-product-media">
        <Link
          className="cc-product-media-link"
          to={`/product/${product.id}`}
          aria-label={`View ${product.name}`}
        >
          {image ? (
            <img src={image} alt={product.name} loading="lazy" />
          ) : (
            <div className="cc-image-fallback" aria-hidden="true">
              {(brand || "C").slice(0, 1)}
            </div>
          )}
        </Link>
        {Number(product.discount_percent || 0) > 0 ? (
          <span className="cc-badge discount">
            {product.discount_percent}% off
          </span>
        ) : null}
        <button
          type="button"
          className={`cc-icon-btn wishlist${wishlisted ? " active" : ""}`}
          onClick={handleWishlist}
          aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
        >
          <FiHeart fill={wishlisted ? "currentColor" : "none"} />
        </button>
      </div>

      <div className="cc-product-body">
        <div className="cc-product-meta">
          {brand ? <span>{brand}</span> : null}
          {category ? <span>{category}</span> : null}
        </div>

        <Link className="cc-product-title" to={`/product/${product.id}`}>
          {product.name}
        </Link>

        {product.rating || product.review_count ? (
          <Rating value={product.rating} count={product.review_count} />
        ) : null}

        <Price price={product.price} comparePrice={product.compare_price} />

        {product.sold_quantity ? (
          <p className="cc-product-sold">
            {Number(product.sold_quantity).toLocaleString("en-IN")} sold
          </p>
        ) : null}

        <div className="cc-product-stock">
          {inStock ? (
            <span className="in">In stock</span>
          ) : (
            <span className="out">Currently unavailable</span>
          )}
        </div>

        <div className="cc-product-actions">
          <button
            type="button"
            className="cc-btn primary full"
            disabled={!inStock || busy}
            onClick={handleCart}
          >
            <FiShoppingCart />
            {busy ? "Adding…" : inStock ? "Add to cart" : "Unavailable"}
          </button>
          <p
            className={`cc-inline-note${notice ? "" : " placeholder"}`}
            role={notice ? "status" : undefined}
            aria-hidden={!notice}
          >
            {notice || "Added to cart"}
          </p>
        </div>
      </div>
    </article>
  );
}

export default memo(ProductCard);
