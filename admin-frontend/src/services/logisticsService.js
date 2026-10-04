import adminApi from "./api";

export async function getLogisticsUsers(search = "", page = 1) {
  const response = await adminApi.get("/admin/logistics", {
    params: { search, page, per_page: 25 },
  });
  return response.data.data;
}

export async function createLogisticsUser(payload) {
  const response = await adminApi.post("/admin/logistics", payload);
  return response.data;
}

export async function updateLogisticsStatus(id, status) {
  const response = await adminApi.put(`/admin/logistics/${id}/status`, {
    status,
  });
  return response.data;
}
