import api from "./api";

export async function createCheckoutSession() {
  const response = await api.post("/checkout/session");
  return response.data.data;
}

export async function getCheckoutSession() {
  const response = await api.get("/checkout/session");
  return response.data.data;
}

export async function validateCheckout() {
  const response = await api.post("/checkout/validate");
  return response.data.data;
}

export async function selectCheckoutAddress(addressId) {
  const response = await api.put("/checkout/address", {
    address_id: addressId,
  });
  return response.data.data;
}

export async function createRazorpayOrder() {
  const response = await api.post("/checkout/razorpay-order");
  return response.data.data;
}

export async function paymentFailed(data) {
  const response = await api.post("/checkout/payment-failed", data);
  return response.data.data;
}

export async function verifyPayment(data) {
  const response = await api.post("/checkout/verify-payment", data);
  return response.data.data;
}

export async function createOrder() {
  const response = await api.post("/checkout/create-order");
  return response.data.data;
}

export async function getMyOrders() {
  const response = await api.get("/orders/");
  return response.data.data ?? [];
}

export async function getActiveOrders() {
  const response = await api.get("/orders/active");
  return response.data.data ?? [];
}

export async function getOrderDetails(orderId) {
  const response = await api.get(`/orders/${orderId}`);
  return response.data.data;
}

export async function getOrderTracking(orderId) {
  const response = await api.get(`/orders/${orderId}/tracking`);
  return response.data.data;
}

export async function getReviewableItems(productId) {
  const suffix = productId ? `?product_id=${Number(productId)}` : "";
  const response = await api.get(`/orders/reviewable${suffix}`);
  return response.data.data ?? [];
}

export async function cancelOrder(orderId, reason) {
  const response = await api.put(
    `/orders/${orderId}/cancel`,
    reason ? { reason } : {},
  );
  return response.data.data;
}

export async function downloadInvoice(orderId) {
  const response = await api.get(`/orders/${orderId}/invoice`, {
    responseType: "blob",
  });
  return response.data;
}
