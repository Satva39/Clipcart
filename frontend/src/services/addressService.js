import api from "./api";

export async function createAddress(data) {
  const response = await api.post("/customer-addresses/", data);
  return response.data.data;
}

export async function getAddresses() {
  const response = await api.get("/customer-addresses/");
  return response.data.data || [];
}

export async function updateAddress(addressId, data) {
  const response = await api.put(`/customer-addresses/${addressId}`, data);
  return response.data.data;
}

export async function setDefaultAddress(addressId) {
  const response = await api.put(`/customer-addresses/${addressId}/default`);
  return response.data.data;
}

export async function deleteAddress(addressId) {
  const response = await api.delete(`/customer-addresses/${addressId}`);
  return response.data;
}
