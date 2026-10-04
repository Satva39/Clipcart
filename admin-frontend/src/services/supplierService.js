import adminApi from "./api";

export async function getSuppliers(search = "", page = 1) {
  const response = await adminApi.get("/admin/suppliers", {
    params: { search, page, per_page: 25 },
  });
  return response.data.data;
}

export async function updateSupplierStatus(supplierId, status) {
  const response = await adminApi.put(`/admin/suppliers/${supplierId}/status`, {
    status,
  });
  return response.data;
}

export async function updateSupplierVerification(supplierId, status) {
  const response = await adminApi.put(
    `/admin/suppliers/${supplierId}/verification`,
    { status },
  );
  return response.data;
}
