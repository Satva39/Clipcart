import supplierApi from "./supplierApi";

export async function getSupplierInventory() {
  const response = await supplierApi.get("/inventory/supplier");
  return response.data.data ?? [];
}

export async function adjustSupplierStock(
  productId,
  amount,
  reason = "MANUAL_ADJUSTMENT",
  options = {},
) {
  const response = await supplierApi.put(
    `/inventory/supplier/${productId}/adjust`,
    {
      amount,
      reason,
      mode: options.mode || "adjust",
      variant_id: options.variantId ?? null,
    },
  );
  return response.data;
}

export async function getInventoryHistory(productId) {
  const response = await supplierApi.get(
    `/inventory/supplier/${productId}/history`,
  );
  return response.data.data ?? [];
}

export async function getInventoryAlerts() {
  const response = await supplierApi.get("/inventory/supplier/alerts");
  return response.data.data ?? { low_stock: [], out_of_stock: [] };
}
