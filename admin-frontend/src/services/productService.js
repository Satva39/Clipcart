import adminApi from "./api";

export async function getAdminProducts(search = "", page = 1) {
  const response = await adminApi.get("/admin/products", {
    params: { search, page, per_page: 25 },
  });
  return response.data.data;
}
export async function createAdminProduct(payload) {
  const response = await adminApi.post("/admin/products", payload);
  return response.data;
}
export async function updateAdminProduct(id, payload) {
  const response = await adminApi.put(`/admin/products/${id}`, payload);
  return response.data;
}
export async function deactivateAdminProduct(id) {
  return adminApi.delete(`/admin/products/${id}`);
}
export async function getCategories() {
  const response = await adminApi.get("/admin/catalog/categories");
  return response.data.data || [];
}
export async function getBrands() {
  const response = await adminApi.get("/admin/catalog/brands");
  return response.data.data || [];
}
export async function createCategory(payload) {
  const response = await adminApi.post("/admin/catalog/categories", payload);
  return response.data;
}
export async function updateCategory(id, payload) {
  const response = await adminApi.put(
    `/admin/catalog/categories/${id}`,
    payload,
  );
  return response.data;
}
export async function createBrand(payload) {
  const response = await adminApi.post("/admin/catalog/brands", payload);
  return response.data;
}
export async function updateBrand(id, payload) {
  const response = await adminApi.put(`/admin/catalog/brands/${id}`, payload);
  return response.data;
}
