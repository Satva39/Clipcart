import adminApi from "./api";

export async function getBanners() {
  const response = await adminApi.get("/admin/banners");
  return response.data.data || [];
}
export async function saveBanner(payload, id = null) {
  const response = id
    ? await adminApi.put(`/admin/banners/${id}`, payload)
    : await adminApi.post("/admin/banners", payload);
  return response.data.data;
}
export async function deactivateBanner(id) {
  return adminApi.delete(`/admin/banners/${id}`);
}

export async function deleteBanner(id) {
  return adminApi.delete(`/admin/banners/${id}/permanent`);
}

export async function uploadBannerImage(file) {
  const form = new FormData();
  form.append("image", file);
  const response = await adminApi.post("/admin/banners/upload", form);
  return response.data.data;
}

export async function getSettings() {
  const response = await adminApi.get("/admin/settings");
  return response.data.data || [];
}
export async function updateSetting(key, payload) {
  const response = await adminApi.put(
    `/admin/settings/${encodeURIComponent(key)}`,
    payload,
  );
  return response.data.data;
}
