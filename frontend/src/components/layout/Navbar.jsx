import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FiBell,
  FiChevronDown,
  FiHeart,
  FiMenu,
  FiSearch,
  FiShoppingCart,
  FiUser,
  FiX,
} from "react-icons/fi";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useCart } from "../../context/CartContext";
import { useWishlist } from "../../context/WishlistContext";
import { getStoreCategories } from "../../services/storeService";
import { getUnreadNotificationCount } from "../../services/notificationService";
import BrandLogo from "../common/BrandLogo";

export default function Navbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { cartCount } = useCart();
  const { items: wishlistItems } = useWishlist();
  const [search, setSearch] = useState("");
  const [accountOpen, setAccountOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const categoriesQuery = useQuery({
    queryKey: ["store", "categories"],
    queryFn: getStoreCategories,
    staleTime: 5 * 60 * 1000,
  });
  const unreadQuery = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: getUnreadNotificationCount,
    enabled: Boolean(user),
    refetchInterval: 60_000,
  });

  function submit(event) {
    event.preventDefault();
    navigate(
      search.trim()
        ? `/search?q=${encodeURIComponent(search.trim())}`
        : "/products",
    );
    setMobileOpen(false);
  }

  function signOut() {
    logout();
    setAccountOpen(false);
    navigate("/");
  }

  return (
    <>
      <header className="cc-header">
        <div className="cc-container cc-header-top">
          <button
            className="cc-mobile-menu"
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <FiMenu />
          </button>
          <Link to="/" className="cc-logo-link" aria-label="Clipcart home">
            <BrandLogo />
          </Link>
          <form className="cc-navbar-search" onSubmit={submit}>
            <span className="cc-search-scope">All</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search products, brands and categories"
              aria-label="Search Clipcart"
            />
            <button type="submit" aria-label="Search">
              <FiSearch />
            </button>
          </form>
          <div className="cc-nav-actions">
            <div className="cc-account-wrap">
              <button
                type="button"
                className="cc-nav-action account"
                onClick={() => setAccountOpen((value) => !value)}
                aria-expanded={accountOpen}
              >
                <FiUser />
                <span>
                  <small>
                    {user
                      ? `Hello, ${user.full_name?.split(" ")[0] || "there"}`
                      : "Hello, sign in"}
                  </small>
                  <strong>
                    Account <FiChevronDown />
                  </strong>
                </span>
              </button>
              {accountOpen ? (
                <div className="cc-account-menu">
                  {user ? (
                    <>
                      <Link to="/profile" onClick={() => setAccountOpen(false)}>
                        Your profile
                      </Link>
                      <Link to="/orders" onClick={() => setAccountOpen(false)}>
                        Your orders
                      </Link>
                      <Link
                        to="/notifications"
                        onClick={() => setAccountOpen(false)}
                      >
                        Notifications
                      </Link>
                      <button type="button" onClick={signOut}>
                        Sign out
                      </button>
                    </>
                  ) : (
                    <>
                      <Link to="/login" onClick={() => setAccountOpen(false)}>
                        Sign in
                      </Link>
                      <Link
                        to="/register"
                        onClick={() => setAccountOpen(false)}
                      >
                        Create account
                      </Link>
                    </>
                  )}
                </div>
              ) : null}
            </div>
            <Link to="/wishlist" className="cc-nav-icon" aria-label="Wishlist">
              <FiHeart />
              {wishlistItems.length > 0 ? (
                <sup>{wishlistItems.length}</sup>
              ) : null}
            </Link>
            {user ? (
              <Link
                to="/notifications"
                className="cc-nav-icon"
                aria-label="Notifications"
              >
                <FiBell />
                {Number(unreadQuery.data || 0) > 0 ? (
                  <sup>{unreadQuery.data}</sup>
                ) : null}
              </Link>
            ) : null}
            <Link to="/cart" className="cc-nav-icon cart" aria-label="Cart">
              <FiShoppingCart />
              {Number(cartCount || 0) > 0 ? <sup>{cartCount}</sup> : null}
            </Link>
          </div>
        </div>
      </header>

      <div className="cc-mobile-search">
        <form className="cc-navbar-search" onSubmit={submit}>
          <FiSearch />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Clipcart"
          />
          <button type="submit">Search</button>
        </form>
      </div>

      {mobileOpen ? (
        <div
          className="cc-mobile-drawer-backdrop"
          onClick={() => setMobileOpen(false)}
        >
          <aside
            className="cc-mobile-drawer"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="cc-mobile-drawer-head">
              <strong>Clipcart</strong>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
              >
                <FiX />
              </button>
            </div>
            <Link to="/products" onClick={() => setMobileOpen(false)}>
              Shop all
            </Link>
            <Link
              to="/products?discount=true"
              onClick={() => setMobileOpen(false)}
            >
              Deals
            </Link>
            {(categoriesQuery.data || []).map((category) => (
              <Link
                key={category.id}
                to={`/products?category=${encodeURIComponent(category.slug)}`}
                onClick={() => setMobileOpen(false)}
              >
                {category.name}
              </Link>
            ))}
            <div className="cc-drawer-divider" />
            <Link
              to={user ? "/profile" : "/login"}
              onClick={() => setMobileOpen(false)}
            >
              {user ? "Your profile" : "Sign in"}
            </Link>
            {user ? (
              <Link to="/orders" onClick={() => setMobileOpen(false)}>
                Your orders
              </Link>
            ) : (
              <Link to="/register" onClick={() => setMobileOpen(false)}>
                Create account
              </Link>
            )}
            <Link to="/wishlist" onClick={() => setMobileOpen(false)}>
              Wishlist
            </Link>
            <Link to="/cart" onClick={() => setMobileOpen(false)}>
              Cart
            </Link>
          </aside>
        </div>
      ) : null}
    </>
  );
}
