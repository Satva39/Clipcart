/* eslint-disable react-refresh/only-export-components */
import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import LogisticsLayout from "./layouts/LogisticsLayout";
import ProtectedLogisticsRoute from "./components/ProtectedLogisticsRoute";

import Login from "./pages/Auth/Login";
const Dashboard = lazy(() => import("./pages/Dashboard/Dashboard"));
const DeliveryQueue = lazy(() => import("./pages/Queue/DeliveryQueue"));
const OrderDetail = lazy(() => import("./pages/Orders/OrderDetail"));
const ReturnDetail = lazy(() => import("./pages/Returns/ReturnDetail"));
const PastDeliveredReturned = lazy(
  () => import("./pages/History/PastDeliveredReturned"),
);

const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    element: <ProtectedLogisticsRoute />,
    children: [
      {
        element: <LogisticsLayout />,
        children: [
          { path: "/", element: <Dashboard /> },
          { path: "/queue", element: <DeliveryQueue /> },
          { path: "/orders/:orderId", element: <OrderDetail /> },
          { path: "/returns/:returnId", element: <ReturnDetail /> },
          {
            path: "/queue/past-delivered-returned",
            element: <PastDeliveredReturned />,
          },
        ],
      },
    ],
  },
]);

export default router;
