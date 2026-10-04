import api from "./api";

export async function getStockAlertStatus(productId, variantId = null) {
  const params = new URLSearchParams({ product_id: String(productId) });
  if (variantId !== null && variantId !== undefined)
    params.set("variant_id", String(variantId));
  const response = await api.get(`/stock-alerts/status?${params.toString()}`);
  return response.data.data;
}

export async function subscribeStockAlert(productId, variantId = null) {
  const response = await api.post("/stock-alerts/", {
    product_id: productId,
    variant_id: variantId,
  });
  return response.data.data;
}

export async function unsubscribeStockAlert(productId, variantId = null) {
  const response = await api.delete("/stock-alerts/", {
    data: { product_id: productId, variant_id: variantId },
  });
  return response.data.data;
}
