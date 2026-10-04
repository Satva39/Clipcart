/* eslint-disable react-refresh/only-export-components */
import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import AdminLayout from "./layouts/AdminLayout";
import ProtectedAdminRoute from "./components/ProtectedAdminRoute";

import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Suppliers = lazy(() => import("./pages/Suppliers"));
const Customers = lazy(() => import("./pages/Customers"));
const Logistics = lazy(() => import("./pages/Logistics"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Banners = lazy(() => import("./pages/Banners"));
const Settings = lazy(() => import("./pages/Settings"));
const Products = lazy(() => import("./pages/Products"));
const Payouts = lazy(() => import("./pages/Payouts"));
const Notifications = lazy(() => import("./pages/Notifications"));
const AuditLogs = lazy(() => import("./pages/AuditLogs"));
const Profile = lazy(() => import("./pages/Profile"));

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/forgot-password", element: <ForgotPassword /> },
  { path: "/reset-password", element: <ResetPassword /> },
  {
    element: <ProtectedAdminRoute />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { path: "/", element: <Dashboard /> },
          { path: "/customers", element: <Customers /> },
          { path: "/suppliers", element: <Suppliers /> },
          { path: "/logistics", element: <Logistics /> },
          { path: "/products", element: <Products /> },
          { path: "/banners", element: <Banners /> },
          { path: "/settings", element: <Settings /> },
          { path: "/payouts", element: <Payouts /> },
          { path: "/analytics", element: <Analytics /> },
          { path: "/notifications", element: <Notifications /> },
          { path: "/audit-logs", element: <AuditLogs /> },
          { path: "/profile", element: <Profile /> },
        ],
      },
    ],
  },
]);

export default router;
