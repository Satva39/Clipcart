import adminApi from "./api";

export async function getAdminDashboard(params = {}) {
  const response = await adminApi.get("/admin/dashboard", { params });
  return response.data.data;
}
