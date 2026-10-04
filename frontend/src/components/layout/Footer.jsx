import { Link } from "react-router-dom";
import BrandLogo from "../common/BrandLogo";

export default function Footer() {
  return (
    <footer className="cc-footer cc-site-footer">
      <div className="cc-container cc-footer-grid">
        <div>
          <Link
            to="/"
            className="cc-logo-link footer"
            aria-label="Clipcart home"
          >
            <BrandLogo footer />
          </Link>
          <p>Marketplace storefront for real products from Clipcart sellers.</p>
        </div>
        <div>
          <strong>Shop</strong>
          <Link to="/products">All products</Link>
          <Link to="/products?discount=true">Deals</Link>
          <Link to="/products?sort=newest">New arrivals</Link>
        </div>
        <div>
          <strong>Account</strong>
          <Link to="/profile">Profile</Link>
          <Link to="/orders">Orders</Link>
          <Link to="/wishlist">Wishlist</Link>
        </div>
        <div>
          <strong>Help</strong>
          <Link to="/cart">Cart</Link>
          <Link to="/checkout">Checkout</Link>
          <Link to="/notifications">Notifications</Link>
        </div>
      </div>
      <div className="cc-footer-bottom">
        <div className="cc-container">
          © {new Date().getFullYear()} Clipcart. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
