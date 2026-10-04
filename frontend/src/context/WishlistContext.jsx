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
  addToWishlist,
  getWishlist,
  removeFromWishlist,
} from "../services/wishlistService";

const WishlistContext = createContext(null);

export function WishlistProvider({ children }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;

    if (!user) {
      setItems([]);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    getWishlist()
      .then((data) => {
        if (active) setItems(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (active) setItems([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [user]);

  const itemIds = useMemo(
    () => new Set(items.map((item) => Number(item.id))),
    [items],
  );

  const toggle = useCallback(
    async (product) => {
      const productId = Number(product.id);
      if (!productId) return false;

      if (itemIds.has(productId)) {
        await removeFromWishlist(productId);
        setItems((current) =>
          current.filter((item) => Number(item.id) !== productId),
        );
        return false;
      }

      await addToWishlist(productId);
      setItems((current) => [
        ...current,
        {
          ...product,
          id: productId,
        },
      ]);
      return true;
    },
    [itemIds],
  );

  const value = useMemo(
    () => ({
      items,
      itemIds,
      loading,
      toggle,
    }),
    [itemIds, items, loading, toggle],
  );

  return (
    <WishlistContext.Provider value={value}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  return useContext(WishlistContext);
}
