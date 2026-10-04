/* eslint-disable react-refresh/only-export-components */
import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import SupplierLayout from "./layouts/SupplierLayout";
import ProtectedSupplierRoute from "./components/ProtectedSupplierRoute";

import Login from "./pages/Auth/Login";
import Register from "./pages/Auth/Register";
import RegisterPayment from "./pages/Auth/RegisterPayment";
import AccountStatus from "./components/AccountStatus";

const Dashboard = lazy(() => import("./pages/Dashboard/Dashboard"));
const Products = lazy(() => import("./pages/Products/Products"));
const AddProduct = lazy(() => import("./pages/Products/AddProduct"));
const Notifications = lazy(() => import("./pages/Notifications/Notifications"));
const Profile = lazy(() => import("./pages/Profile/Profile"));
const EditProduct = lazy(() => import("./pages/Products/EditProduct"));
const Orders = lazy(() => import("./pages/Orders/Orders"));
const OrderDetails = lazy(() => import("./pages/Orders/OrderDetails"));
const Earnings = lazy(() => import("./pages/Earnings/Earnings"));
const Inventory = lazy(() => import("./pages/Inventory/Inventory"));
const Analytics = lazy(() => import("./pages/Analytics/Analytics"));

const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },

  {
    path: "/register",
    element: <Register />,
  },

  {
    path: "/register/payment",
    element: <RegisterPayment />,
  },

  {
    path: "/account-status",
    element: <AccountStatus />,
  },

  {
    element: <ProtectedSupplierRoute />,
    children: [
      {
        element: <SupplierLayout />,
        children: [
          {
            path: "/",
            element: <Dashboard />,
          },
          {
            path: "/products/add",
            element: <AddProduct />,
          },
          {
            path: "/products/:productId/edit",
            element: <EditProduct />,
          },
          {
            path: "/products",
            element: <Products />,
          },
          {
            path: "/orders",
            element: <Orders />,
          },
          {
            path: "/orders/:orderId",
            element: <OrderDetails />,
          },
          {
            path: "/inventory",
            element: <Inventory />,
          },
          {
            path: "/analytics",
            element: <Analytics />,
          },
          {
            path: "/earnings",
            element: <Earnings />,
          },
          {
            path: "/notifications",
            element: <Notifications />,
          },
          {
            path: "/profile",
            element: <Profile />,
          },
        ],
      },
    ],
  },
]);

export default router;
