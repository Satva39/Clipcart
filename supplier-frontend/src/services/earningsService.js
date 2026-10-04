import api from "./api";
export async function getSupplierEarnings() {
  const response = await api.get("/orders/supplier/earnings");
  return response.data.data ?? {};
}
