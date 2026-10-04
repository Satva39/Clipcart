/* eslint-disable react-refresh/only-export-components */
import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import SupplierLayout from "../layouts/SupplierLayout";
import ProtectedRoute from "../components/auth/ProtectedRoute";
import NotFound from "../pages/Error/NotFound";

const Home = lazy(() => import("../pages/Home/Home"));
const Login = lazy(() => import("../pages/Auth/Login"));
const Register = lazy(() => import("../pages/Auth/Register"));
const SearchPage = lazy(() => import("../pages/Search/SearchPage"));
const ProductPage = lazy(() => import("../pages/Product/ProductPage"));
const CartPage = lazy(() => import("../pages/Cart/CartPage"));
const WishlistPage = lazy(() => import("../pages/Wishlist/WishlistPage"));
const ProfilePage = lazy(() => import("../pages/Profile/ProfilePage"));
const Notifications = lazy(
  () => import("../pages/Notifications/Notifications"),
);
const Checkout = lazy(() => import("../pages/Checkout/Checkout"));
const Orders = lazy(() => import("../pages/Orders/Orders"));
const OrderDetails = lazy(() => import("../pages/Orders/OrderDetails"));
const OrderSuccess = lazy(() => import("../pages/OrderSuccess/OrderSuccess"));
const CustomerDashboard = lazy(() => import("../pages/Customer/Dashboard"));
const SupplierDashboard = lazy(() => import("../pages/Supplier/Dashboard"));

const customerRoutes = {
  element: <ProtectedRoute />,
  children: [
    { path: "profile", element: <ProfilePage /> },
    { path: "notifications", element: <Notifications /> },
    { path: "checkout", element: <Checkout /> },
    { path: "orders", element: <Orders /> },
    { path: "orders/:orderId", element: <OrderDetails /> },
    { path: "track-order/:orderId", element: <OrderDetails /> },
    { path: "order-success", element: <OrderSuccess /> },
    { path: "customer", element: <CustomerDashboard /> },
  ],
};

const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    errorElement: <NotFound />,
    children: [
      { index: true, element: <Home /> },
      { path: "search", element: <SearchPage /> },
      { path: "products", element: <SearchPage /> },
      { path: "product/:id", element: <ProductPage /> },
      { path: "cart", element: <CartPage /> },
      { path: "wishlist", element: <WishlistPage /> },
      { path: "login", element: <Login /> },
      { path: "register", element: <Register /> },
      customerRoutes,
    ],
  },
  {
    path: "/supplier",
    element: <SupplierLayout />,
    children: [{ index: true, element: <SupplierDashboard /> }],
  },
]);

export default router;
