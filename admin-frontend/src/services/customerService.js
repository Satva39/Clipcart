import adminApi from "./api";

export async function getCustomers(search = "", page = 1) {
  const response = await adminApi.get("/admin/customers", {
    params: { search, page, per_page: 25 },
  });
  return response.data.data;
}

export async function updateCustomerStatus(customerId, status) {
  const response = await adminApi.put(`/admin/customers/${customerId}/status`, {
    status,
  });
  return response.data;
}
