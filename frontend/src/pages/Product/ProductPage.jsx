import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  FiBell,
  FiCheck,
  FiHeart,
  FiShare2,
  FiShoppingCart,
  FiTruck,
  FiZap,
} from "react-icons/fi";
import { useCart } from "../../context/CartContext";
import { useAuth } from "../../context/AuthContext";
import { useWishlist } from "../../context/WishlistContext";
import ProductReviews from "../../components/product/ProductReviews";
import {
  getStockAlertStatus,
  subscribeStockAlert,
  unsubscribeStockAlert,
} from "../../services/stockAlertService";
import {
  getRelatedProducts,
  getProductById,
} from "../../services/productService";
import { getApiMessage } from "../../utils/apiError";
import {
  discountPercent,
  getBrandName,
  getCategoryName,
} from "../../utils/formatters";
import { rememberRecentlyViewed } from "../../utils/recentlyViewed";
import Container from "../../components/common/Container";
import { ErrorState, LoadingState } from "../../components/common/AsyncState";
import ProductCard from "../../components/product/ProductCard";
import Price from "../../components/product/Price";
import Rating from "../../components/product/Rating";

function getVariantLabel(variant) {
  const optionValues = variant?.option_values;
  if (
    optionValues &&
    typeof optionValues === "object" &&
    !Array.isArray(optionValues)
  ) {
    const parts = Object.entries(optionValues)
      .filter(([, value]) => String(value ?? "").trim())
      .map(([name, value]) => `${name}: ${value}`);
    if (parts.length) return parts.join(" · ");
  }

  const name = String(variant?.name || "").trim();
  const value = String(variant?.value || "").trim();
  if (name && value && name !== value) return `${name}: ${value}`;
  return value || name || `Variant ${variant?.id || ""}`.trim();
}

export default function ProductPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToCart } = useCart();
  const { itemIds, toggle } = useWishlist();
  const queryClient = useQueryClient();
  const [selectedVariantId, setSelectedVariantId] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [selectedImage, setSelectedImage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [stockAlertBusy, setStockAlertBusy] = useState(false);

  const productQuery = useQuery({
    queryKey: ["store", "product", id],
    queryFn: () => getProductById(id),
  });
  const product = productQuery.data;

  const relatedQuery = useQuery({
    queryKey: ["related", id],
    queryFn: () => getRelatedProducts(id),
    enabled: Boolean(product),
  });

  const availableVariants = useMemo(
    () =>
      (Array.isArray(product?.variants) ? product.variants : []).filter(
        (item) => item && item.is_active !== false,
      ),
    [product],
  );

  const variant = useMemo(
    () =>
      availableVariants.find(
        (item) => Number(item.id) === Number(selectedVariantId),
      ) ||
      availableVariants[0] ||
      null,
    [availableVariants, selectedVariantId],
  );

  useEffect(() => {
    if (!availableVariants.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (selectedVariantId !== null) setSelectedVariantId(null);
      return;
    }

    const selectedExists = availableVariants.some(
      (item) => Number(item.id) === Number(selectedVariantId),
    );

    if (!selectedExists) {
      setSelectedVariantId(availableVariants[0].id);
      setSelectedImage(availableVariants[0].images?.[0]?.url || null);
    }
  }, [availableVariants, selectedVariantId]);

  const currentPrice = variant?.price ?? product?.price ?? 0;
  const currentComparePrice =
    variant?.compare_price ?? product?.compare_price ?? null;
  const currentStock = variant?.stock ?? product?.stock ?? 0;
  const stockAlertQuery = useQuery({
    queryKey: ["stock-alert", id, selectedVariantId],
    queryFn: () => getStockAlertStatus(id, selectedVariantId),
    enabled: Boolean(user && product && currentStock <= 0),
  });
  const stockAlertSubscribed = Boolean(stockAlertQuery.data?.subscribed);
  const wishlist = itemIds.has(Number(product?.id));
  const baseImages = product?.images || [];
  const variantImages = variant?.images || [];
  const gallery = variantImages.length
    ? variantImages.map((item) => ({ ...item, variantImage: true }))
    : baseImages;
  const activeImage =
    selectedImage ||
    gallery.find((image) => image.primary)?.url ||
    gallery[0]?.url ||
    product?.image ||
    null;

  useEffect(() => {
    if (product?.id) rememberRecentlyViewed(product);
  }, [product]);

  if (productQuery.isLoading)
    return (
      <div className="cc-page-shell">
        <Container>
          <LoadingState label="Loading product…" />
        </Container>
      </div>
    );
  if (productQuery.isError || !product)
    return (
      <div className="cc-page-shell">
        <Container>
          <ErrorState
            message="This product could not be loaded."
            onRetry={() => productQuery.refetch()}
          />
        </Container>
      </div>
    );

  async function addCurrentToCart() {
    if (currentStock <= 0 || busy) return false;
    setBusy(true);
    setMessage("");
    try {
      await addToCart(
        {
          ...product,
          price: currentPrice,
          stock: currentStock,
          variant_id: variant?.id ?? null,
          image: activeImage,
        },
        quantity,
      );
      setMessage("Added to cart.");
      return true;
    } catch (error) {
      setMessage(
        getApiMessage(error, "Couldn't add this product to your cart."),
      );
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function buyNow() {
    const added = await addCurrentToCart();
    if (added) navigate("/checkout");
  }

  async function handleWishlist() {
    if (!user) {
      navigate(
        `/login?redirect=${encodeURIComponent(window.location.pathname)}`,
      );
      return;
    }
    try {
      await toggle(product);
      setMessage(wishlist ? "Removed from wishlist." : "Saved to wishlist.");
    } catch (error) {
      setMessage(getApiMessage(error, "Couldn't update your wishlist."));
    }
  }

  async function share() {
    try {
      if (navigator.share) {
        await navigator.share({
          title: product.name,
          text: product.description || product.name,
          url: window.location.href,
        });
        return;
      }
      await navigator.clipboard.writeText(window.location.href);
      setMessage("Product link copied.");
    } catch {
      setMessage("Sharing is not available in this browser.");
    }
  }

  const category = getCategoryName(product.category);
  const brand = getBrandName(product.brand);
  const reviewAverage = product.review_summary?.average ?? product.rating ?? 0;
  const reviewCount =
    product.review_summary?.count ?? product.review_count ?? 0;

  return (
    <div className="cc-page-shell">
      <Container>
        <nav className="cc-breadcrumbs">
          <Link to="/">Home</Link>
          <span>/</span>
          {category ? (
            <>
              <Link to={`/products?category=${product.category?.slug || ""}`}>
                {category}
              </Link>
              <span>/</span>
            </>
          ) : null}
          <span>{product.name}</span>
        </nav>

        <div className="cc-product-detail">
          <div className="cc-gallery">
            <div className="cc-gallery-thumbs" aria-label="Product images">
              {gallery.map((image) => (
                <button
                  key={image.id || image.url}
                  type="button"
                  className={activeImage === image.url ? "active" : ""}
                  onClick={() => setSelectedImage(image.url)}
                >
                  <img src={image.url} alt="" loading="lazy" decoding="async" />
                </button>
              ))}
            </div>
            <div className="cc-gallery-main">
              {activeImage ? (
                <img src={activeImage} alt={product.name} />
              ) : (
                <div className="cc-image-fallback large">
                  {product.name.slice(0, 1)}
                </div>
              )}
            </div>
          </div>

          <div className="cc-product-info">
            <div className="cc-product-meta">
              {brand ? <span>{brand}</span> : null}
              {category ? <span>{category}</span> : null}
            </div>
            <h1>{product.name}</h1>
            <div className="cc-detail-rating">
              <Rating value={reviewAverage} count={reviewCount} />
              <span>Customer reviews</span>
            </div>
            <Price
              price={currentPrice}
              comparePrice={currentComparePrice}
              size="lg"
            />
            {currentComparePrice &&
            discountPercent(currentPrice, currentComparePrice) > 0 ? (
              <p className="cc-tax-note">
                MRP and discount are based on the product data supplied by the
                seller.
              </p>
            ) : null}

            {availableVariants.length ? (
              <div className="cc-variant-groups">
                <div>
                  <strong>Choose a variant</strong>
                  <div className="cc-variant-list">
                    {availableVariants.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className={variant?.id === item.id ? "active" : ""}
                        aria-pressed={variant?.id === item.id}
                        onClick={() => {
                          setSelectedVariantId(item.id);
                          setSelectedImage(item.images?.[0]?.url || null);
                          setQuantity(1);
                        }}
                      >
                        {getVariantLabel(item)}
                        {Number(item.stock || 0) <= 0 ? " · Out" : ""}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}

            <div className="cc-stock-row">
              <span className={currentStock > 0 ? "in" : "out"}>
                {currentStock > 0
                  ? `${currentStock} in stock`
                  : "Currently unavailable"}
              </span>
              {currentStock > 0 ? (
                <span>
                  Seller:{" "}
                  {product.seller?.name || "Seller information unavailable"}
                </span>
              ) : null}
            </div>

            {currentStock > 0 ? (
              <div className="cc-buy-box">
                <div className="cc-qty">
                  <button
                    type="button"
                    onClick={() =>
                      setQuantity((value) => Math.max(1, value - 1))
                    }
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <span>{quantity}</span>
                  <button
                    type="button"
                    onClick={() =>
                      setQuantity((value) => Math.min(currentStock, value + 1))
                    }
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>
                <button
                  type="button"
                  className="cc-btn secondary"
                  onClick={addCurrentToCart}
                  disabled={busy}
                >
                  <FiShoppingCart />
                  {busy ? "Adding…" : "Add to cart"}
                </button>
                <button
                  type="button"
                  className="cc-btn primary"
                  onClick={buyNow}
                  disabled={busy}
                >
                  <FiZap />
                  Buy now
                </button>
              </div>
            ) : (
              <div className="cc-unavailable-panel">
                {user ? (
                  <>
                    <button
                      type="button"
                      className="cc-btn secondary full"
                      disabled={stockAlertBusy}
                      onClick={async () => {
                        try {
                          setStockAlertBusy(true);
                          if (stockAlertSubscribed) {
                            await unsubscribeStockAlert(
                              product.id,
                              variant?.id ?? null,
                            );
                            await queryClient.invalidateQueries({
                              queryKey: ["stock-alert", id, selectedVariantId],
                            });
                            setMessage("Stock alert removed.");
                          } else {
                            await subscribeStockAlert(
                              product.id,
                              variant?.id ?? null,
                            );
                            await queryClient.invalidateQueries({
                              queryKey: ["stock-alert", id, selectedVariantId],
                            });
                            setMessage(
                              "We’ll notify you when this item is available.",
                            );
                          }
                        } catch (error) {
                          setMessage(
                            getApiMessage(
                              error,
                              "Could not update the stock alert.",
                            ),
                          );
                        } finally {
                          setStockAlertBusy(false);
                        }
                      }}
                    >
                      <FiBell />
                      {stockAlertBusy
                        ? "Updating…"
                        : stockAlertSubscribed
                          ? "Notify me enabled"
                          : "Notify me when available"}
                    </button>
                    <small>
                      {stockAlertSubscribed
                        ? "You’ll get an account notification when stock is replenished."
                        : "We’ll keep one alert subscription for this item."}
                    </small>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="cc-btn secondary full"
                      onClick={() =>
                        navigate(
                          `/login?redirect=${encodeURIComponent(window.location.pathname)}`,
                        )
                      }
                    >
                      <FiBell /> Sign in to get a stock alert
                    </button>
                    <small>
                      Stock alerts are tied to your Clipcart account.
                    </small>
                  </>
                )}
              </div>
            )}

            <div className="cc-action-row">
              <button
                type="button"
                className={wishlist ? "active" : ""}
                onClick={handleWishlist}
              >
                <FiHeart fill={wishlist ? "currentColor" : "none"} />{" "}
                {wishlist ? "Saved" : "Wishlist"}
              </button>
              <button type="button" onClick={share}>
                <FiShare2 /> Share
              </button>
            </div>
            {message ? (
              <div className="cc-inline-message" role="status">
                {message}
              </div>
            ) : null}

            <div className="cc-trust-grid">
              {currentStock > 0 ? (
                <div>
                  <FiCheck />
                  <span>
                    <strong>In stock</strong>
                    <small>Inventory comes from Clipcart.</small>
                  </span>
                </div>
              ) : null}
              {product.seller?.name ? (
                <div>
                  <FiCheck />
                  <span>
                    <strong>{product.seller.name}</strong>
                    <small>Seller on this listing.</small>
                  </span>
                </div>
              ) : null}
              <div>
                <FiTruck />
                <span>
                  <strong>Delivery details</strong>
                  <small>
                    Address and delivery terms are confirmed at checkout.
                  </small>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="cc-detail-sections">
          <section className="cc-detail-panel">
            <h2>Description</h2>
            <p>
              {product.description ||
                "No product description was supplied by the seller."}
            </p>
          </section>
          <section className="cc-detail-panel">
            <h2>Seller</h2>
            <p>
              {product.seller?.name ||
                "Seller information is not available for this listing."}
            </p>
          </section>
        </div>

        <ProductReviews productId={id} />

        {relatedQuery.data?.length ? (
          <section className="cc-section">
            <div className="cc-section-header">
              <h2>Related products</h2>
            </div>
            <div className="cc-product-grid shelf">
              {relatedQuery.data.slice(0, 4).map((item) => (
                <ProductCard key={item.id} product={item} />
              ))}
            </div>
          </section>
        ) : null}
      </Container>
    </div>
  );
}
