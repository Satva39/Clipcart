import api from "./api";

export async function getReturns() {
  const response = await api.get("/returns/");
  return response.data.data ?? [];
}

export async function createReturn(data) {
  const response = await api.post("/returns/", data);
  return response.data.data;
}

export async function cancelReturn(returnId) {
  const response = await api.put(`/returns/${returnId}/cancel`);
  return response.data.data;
}
