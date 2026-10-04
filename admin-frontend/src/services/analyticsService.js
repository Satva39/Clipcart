import adminApi from "./api";

export async function getAdminAnalytics(params = {}) {
  const response = await adminApi.get("/admin/analytics", { params });
  return response.data.data;
}
