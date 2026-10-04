import api from "./api";

export async function getSupplierDashboard(range) {
  const response = await api.get("/supplier/portal/dashboard", {
    params: range,
  });
  return response.data.data;
}

export async function getSupplierAnalytics(range) {
  const response = await api.get("/supplier/portal/analytics", {
    params: range,
  });
  return response.data.data;
}

export async function getSupplierCatalog(params = {}) {
  const response = await api.get("/supplier/portal/catalog", { params });
  return response.data.data;
}

export async function getSupplierProfile() {
  const response = await api.get("/supplier/portal/profile");
  return response.data.data;
}

export async function updateSupplierProfile(data) {
  const response = await api.put("/supplier/portal/profile", data);
  return response.data.data;
}

export async function downloadSupplierExport(kind, params = {}) {
  const response = await api.get(`/supplier/portal/export/${kind}`, {
    params,
    responseType: "blob",
  });
  const blob = new Blob([response.data], { type: "text/csv;charset=utf-8" });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `clipcart-supplier-${kind}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
