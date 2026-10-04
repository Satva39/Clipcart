import { useState } from "react";
import { FaHeart } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";

export default function ProductActions({ product }) {
  const { addToCart } = useCart();
  const { user } = useAuth();
  const { itemIds, toggle: toggleWishlist } = useWishlist();
  const navigate = useNavigate();

  const stock = Number(product.stock || 0);

  const [quantity, setQuantity] = useState(1);

  const [wishlistLoading, setWishlistLoading] = useState(false);
  const wishlisted = itemIds.has(Number(product.id));

  async function handleWishlist() {
    if (wishlistLoading) return;

    if (!user) {
      navigate("/login");
      return;
    }

    try {
      setWishlistLoading(true);
      await toggleWishlist(product);
    } catch (error) {
      console.error("Wishlist error:", error);
    } finally {
      setWishlistLoading(false);
    }
  }

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const isOutOfStock = stock <= 0;

  function decreaseQuantity() {
    setQuantity((current) => Math.max(1, current - 1));
    setMessage("");
  }

  function increaseQuantity() {
    setQuantity((current) => {
      if (stock > 0 && current >= stock) {
        return current;
      }

      return current + 1;
    });

    setMessage("");
  }

  async function handleAddToCart() {
    if (isOutOfStock) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");

      await addToCart(product, quantity);

      setMessage(`${quantity} item${quantity > 1 ? "s" : ""} added to cart.`);
    } catch (err) {
      console.error("Add to cart error:", err);

      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to add this product to cart.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleBuyNow() {
    if (isOutOfStock) {
      return;
    }

    try {
      setLoading(true);
      setError("");

      await addToCart(product, quantity);

      navigate("/cart");
    } catch (err) {
      console.error("Buy now error:", err);

      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to continue with this product.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-8">
      {/* Quantity */}
      <div className="flex items-center gap-4">
        <span className="font-semibold text-white">Quantity</span>

        <div className="flex items-center overflow-hidden rounded-lg border border-gray-300 bg-white">
          <button
            type="button"
            onClick={decreaseQuantity}
            disabled={loading}
            className="px-5 py-3 text-lg text-gray-800 transition hover:bg-gray-100 disabled:opacity-50"
          >
            −
          </button>

          <span className="min-w-14 border-x border-gray-300 px-4 py-3 text-center font-semibold text-gray-800">
            {quantity}
          </span>

          <button
            type="button"
            onClick={increaseQuantity}
            disabled={loading || (stock > 0 && quantity >= stock)}
            className="px-5 py-3 text-lg text-gray-800 transition hover:bg-gray-100 disabled:opacity-50"
          >
            +
          </button>
        </div>
      </div>

      {/* Buttons */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={handleWishlist}
          disabled={wishlistLoading}
          className={`flex items-center justify-center gap-2 rounded-xl border px-6 py-4 font-bold transition ${
            wishlisted
              ? "border-red-500 bg-red-500 text-white"
              : "border-gray-500 bg-[#131921] text-white hover:border-[#FFB703] hover:text-[#FFB703]"
          }`}
        >
          <FaHeart />
          {wishlisted ? "Wishlisted" : "Wishlist"}
        </button>

        <button
          type="button"
          onClick={handleAddToCart}
          disabled={loading || isOutOfStock}
          className="rounded-xl border-2 border-[#FFB703] bg-[#FFB703] px-6 py-4 font-bold text-black transition hover:bg-[#f5aa00] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Processing..." : "Add to Cart"}
        </button>

        <button
          type="button"
          onClick={handleBuyNow}
          disabled={loading || isOutOfStock}
          className="rounded-xl border-2 border-[#FF5A1F] bg-[#FF5A1F] px-6 py-4 font-bold text-white transition hover:bg-[#e84e19] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Buy Now
        </button>
      </div>

      {message && (
        <p className="mt-4 rounded-lg bg-green-50 px-4 py-3 text-sm font-semibold text-green-700">
          {message}
        </p>
      )}

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm font-semibold text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
