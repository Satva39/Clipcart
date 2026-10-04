import adminApi from "./api";

export async function getAdminOrders(search = "", status = "") {
  const params = {};

  if (search) {
    params.search = search;
  }

  if (status) {
    params.status = status;
  }

  const response = await adminApi.get("/admin/orders", { params });

  return response.data.data ?? [];
}

export async function getAdminOrder(orderId) {
  const response = await adminApi.get(`/admin/orders/${orderId}`);

  return response.data.data;
}

export async function retryAdminShipment(orderId) {
  const response = await adminApi.post(`/admin/shipments/${orderId}/retry`);
  return response.data.data ?? [];
}
