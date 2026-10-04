/* eslint-disable react-refresh/only-export-components */
/* eslint-disable react-hooks/set-state-in-effect */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useAuth } from "./AuthContext";
import {
  addToCart as addCartItem,
  getCart,
  removeFromCart as removeCartItem,
  updateCart as updateCartItem,
} from "../services/cartService";

const CartContext = createContext(null);
const GUEST_CART_KEY = "clipcart_guest_cart";

function mapBackendCart(items = []) {
  return items.map((item) => ({
    id: `${item.product_id}-${item.variant_id ?? "default"}`,
    product_id: item.product_id,
    variant_id: item.variant_id,
    name: item.name,
    slug: item.slug,
    category: item.category,
    brand: item.brand,
    compare_price: item.compare_price,
    variant_name: item.variant_name,
    variant_value: item.variant_value,
    price: Number(item.price || 0),
    quantity: Number(item.quantity || 0),
    stock: Number(item.stock || 0),
    image: item.image,
    item_total: Number(item.item_total || 0),
  }));
}

function loadGuestCart() {
  try {
    const value = localStorage.getItem(GUEST_CART_KEY);
    return value ? JSON.parse(value) : [];
  } catch {
    return [];
  }
}

function saveGuestCart(items) {
  localStorage.setItem(GUEST_CART_KEY, JSON.stringify(items));
}

export function CartProvider({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [cartItems, setCartItems] = useState(loadGuestCart);
  const [cartLoading, setCartLoading] = useState(false);

  const refreshBackendCart = useCallback(async () => {
    const data = await getCart();
    setCartItems(mapBackendCart(data?.items || []));
  }, []);

  useEffect(() => {
    if (authLoading) return;

    if (!user) {
      setCartItems(loadGuestCart());
      return;
    }

    let active = true;
    async function syncGuestCart() {
      const guestItems = loadGuestCart();
      try {
        setCartLoading(true);
        for (const item of guestItems) {
          try {
            await addCartItem(item.product_id, item.quantity, item.variant_id);
          } catch {
            // The backend remains the source of truth when a guest item is no longer valid.
          }
        }
        const data = await getCart();
        if (active) setCartItems(mapBackendCart(data?.items || []));
        localStorage.removeItem(GUEST_CART_KEY);
      } catch {
        if (active) setCartItems([]);
      } finally {
        if (active) setCartLoading(false);
      }
    }

    syncGuestCart();
    return () => {
      active = false;
    };
  }, [user, authLoading]);

  useEffect(() => {
    if (!user && !authLoading) saveGuestCart(cartItems);
  }, [cartItems, user, authLoading]);

  const addToCart = useCallback(
    async (product, quantity = 1) => {
      const variantId = product.variant_id ?? null;
      if (user) {
        await addCartItem(
          product.product_id || product.id,
          quantity,
          variantId,
        );
        await refreshBackendCart();
        return;
      }

      setCartItems((current) => {
        const itemId = `${product.product_id || product.id}-${variantId ?? "default"}`;
        const existing = current.find((item) => item.id === itemId);
        if (existing) {
          return current.map((item) =>
            item.id === itemId
              ? { ...item, quantity: item.quantity + quantity }
              : item,
          );
        }
        return [
          ...current,
          {
            ...product,
            id: itemId,
            product_id: product.product_id || product.id,
            variant_id: variantId,
            quantity,
            price: Number(product.price || 0),
            stock: Number(product.stock || 0),
          },
        ];
      });
    },
    [refreshBackendCart, user],
  );

  const removeFromCart = useCallback(
    async (productId, variantId = null) => {
      if (user) {
        await removeCartItem(productId, variantId);
        await refreshBackendCart();
        return;
      }

      setCartItems((current) =>
        current.filter(
          (item) =>
            !(
              item.product_id === productId &&
              (variantId === null || item.variant_id === variantId)
            ),
        ),
      );
    },
    [refreshBackendCart, user],
  );

  const updateQuantity = useCallback(
    async (productId, quantity, variantId = null) => {
      if (quantity <= 0) {
        await removeFromCart(productId, variantId);
        return;
      }

      if (user) {
        await updateCartItem(productId, quantity, variantId);
        await refreshBackendCart();
        return;
      }

      setCartItems((current) =>
        current.map((item) =>
          item.product_id === productId &&
          (variantId === null || item.variant_id === variantId)
            ? { ...item, quantity }
            : item,
        ),
      );
    },
    [refreshBackendCart, removeFromCart, user],
  );

  const clearCart = useCallback(async () => {
    if (user) {
      const current = [...cartItems];
      for (const item of current) {
        try {
          await removeCartItem(item.product_id, item.variant_id);
        } catch {
          // Continue removing the remaining backend items.
        }
      }
      await refreshBackendCart();
      return;
    }

    setCartItems([]);
    localStorage.removeItem(GUEST_CART_KEY);
  }, [cartItems, refreshBackendCart, user]);

  const cartCount = useMemo(
    () =>
      cartItems.reduce((total, item) => total + Number(item.quantity || 0), 0),
    [cartItems],
  );

  const cartSubtotal = useMemo(
    () =>
      cartItems.reduce(
        (total, item) =>
          total + Number(item.price || 0) * Number(item.quantity || 0),
        0,
      ),
    [cartItems],
  );

  const value = useMemo(
    () => ({
      cartItems,
      cartCount,
      cartSubtotal,
      cartLoading,
      addToCart,
      updateQuantity,
      removeFromCart,
      clearCart,
    }),
    [
      addToCart,
      cartCount,
      cartItems,
      cartLoading,
      cartSubtotal,
      clearCart,
      removeFromCart,
      updateQuantity,
    ],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  return useContext(CartContext);
}
