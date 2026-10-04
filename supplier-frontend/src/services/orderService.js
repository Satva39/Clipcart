import api from "./api";

export async function getSupplierOrders(params = {}) {
  const response = await api.get("/orders/supplier", { params });
  const data = response.data.data;
  return Array.isArray(data)
    ? {
        orders: data,
        pagination: {
          page: 1,
          per_page: data.length || 25,
          pages: 1,
          total: data.length,
        },
      }
    : {
        orders: data?.orders ?? [],
        pagination: data?.pagination ?? { page: 1, pages: 0, total: 0 },
      };
}

export async function getSupplierOrderDetails(orderId) {
  const response = await api.get(`/orders/supplier/${orderId}`);
  return response.data.data;
}

export async function updateSupplierOrderStatus(orderId, status) {
  const response = await api.put(`/orders/supplier/${orderId}/status`, {
    status,
  });
  return response.data;
}

export async function importSupplierOrders(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await api.post("/supplier/portal/import/orders", form);
  return response.data;
}
