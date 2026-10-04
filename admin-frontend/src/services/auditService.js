import adminApi from "./api";

export async function getAuditLogs(page = 1) {
  const response = await adminApi.get("/admin/audit-logs", {
    params: { page, per_page: 50 },
  });
  return response.data.data;
}
