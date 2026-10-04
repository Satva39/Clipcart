import adminApi from "./api";

export async function getPayouts(status = "", page = 1) {
  const response = await adminApi.get("/payouts/admin/requests", {
    params: { status, page, per_page: 25 },
  });
  return Array.isArray(response.data?.data) ? response.data.data : [];
}

export async function updatePayoutStatus(id, status) {
  const response = await adminApi.put(`/payouts/admin/requests/${id}/status`, {
    status,
  });
  return response.data;
}

export async function getPayoutAccounts() {
  const response = await adminApi.get("/payouts/admin/accounts");
  return Array.isArray(response.data?.data) ? response.data.data : [];
}

export async function verifyPayoutAccount(id) {
  const response = await adminApi.put(`/payouts/admin/accounts/${id}/verify`);
  return response.data;
}
