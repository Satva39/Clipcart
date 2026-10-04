import api from "./api";

export async function registerSupplier(data) {
  const response = await api.post("/supplier-registration/", data);

  return response.data.data;
}

export async function createRegistrationPayment() {
  const response = await api.post("/supplier-registration/payment/order");

  return response.data.data;
}

export async function verifyRegistrationPayment(data) {
  const response = await api.post(
    "/supplier-registration/payment/verify",
    data,
  );

  return response.data;
}
export async function getRegistrationStatus() {
  const response = await api.get("/supplier-registration/status");
  return response.data.data;
}
