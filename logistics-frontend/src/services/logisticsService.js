import api from "./api";

export async function login(email, password) {
  const response = await api.post("/logistics/auth/login", {
    email,
    password,
  });
  return response.data.data;
}

export async function getMe() {
  const response = await api.get("/logistics/auth/me");
  return response.data.data;
}

export async function getDashboard() {
  const response = await api.get("/logistics/dashboard");
  return response.data.data;
}

export async function getQueue(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
  const response = await api.get("/logistics/orders", { params: clean });
  return response.data.data ?? [];
}

export async function getOrder(orderId) {
  const response = await api.get(`/logistics/orders/${orderId}`);
  return response.data.data;
}

export async function assignAgent(orderId, agentName, agentPhone) {
  const response = await api.put(`/logistics/orders/${orderId}/assign`, {
    agent_name: agentName,
    agent_phone: agentPhone,
  });
  return response.data.data;
}

export async function markPickedUp(orderId) {
  const response = await api.put(`/logistics/orders/${orderId}/pickup`);
  return response.data.data;
}

export async function markOutForDelivery(orderId) {
  const response = await api.put(
    `/logistics/orders/${orderId}/out-for-delivery`,
  );
  return response.data.data;
}

export async function recordAttempt(orderId, reason, notes = "") {
  const response = await api.put(`/logistics/orders/${orderId}/attempt`, {
    reason,
    notes,
  });
  return response.data.data;
}

export async function markDelivered(
  orderId,
  {
    notes = "",
    customer_delivery_notes = "",
    proof_of_delivery_reference = "",
    completion_photo,
  } = {},
) {
  const form = new FormData();
  form.append("notes", notes);
  form.append("customer_delivery_notes", customer_delivery_notes);
  form.append("proof_of_delivery_reference", proof_of_delivery_reference);
  if (completion_photo) {
    form.append("completion_photo", completion_photo);
  }

  const response = await api.put(`/logistics/orders/${orderId}/deliver`, form, {
    headers: { "Content-Type": undefined },
  });
  return response.data.data;
}

export async function markFailed(orderId, reason, nextAction, notes = "") {
  const response = await api.put(`/logistics/orders/${orderId}/fail`, {
    reason,
    next_action: nextAction,
    notes,
  });
  return response.data.data;
}

export async function retryFailed(orderId, notes = "") {
  const response = await api.put(`/logistics/orders/${orderId}/retry`, {
    notes,
  });
  return response.data.data;
}

export async function getNotifications(unread = false) {
  const response = await api.get("/logistics/notifications", {
    params: unread ? { unread: "true" } : undefined,
  });
  return response.data.data ?? [];
}

export async function markNotificationRead(notificationId) {
  const response = await api.put(
    `/logistics/notifications/${notificationId}/read`,
  );
  return response.data.data;
}

export async function markAllNotificationsRead() {
  const response = await api.put("/logistics/notifications/read-all");
  return response.data.data;
}

export async function getReturns() {
  const response = await api.get("/returns/logistics");
  return response.data.data ?? [];
}

export async function getReturn(returnId) {
  const response = await api.get(`/returns/logistics/${returnId}`);
  return response.data.data;
}

export async function assignReturnPickup(
  returnId,
  agentName,
  agentPhone,
  notes = "",
) {
  const response = await api.put(`/returns/logistics/${returnId}/assign`, {
    agent_name: agentName,
    agent_phone: agentPhone,
    notes,
  });
  return response.data.data;
}

export async function markReturnPickedUp(returnId, notes = "") {
  const response = await api.put(`/returns/logistics/${returnId}/pickup`, {
    notes,
  });
  return response.data.data;
}

export async function markReturnDeliveredToSupplier(
  returnId,
  notes = "",
  completionPhoto,
) {
  const form = new FormData();
  form.append("notes", notes);
  if (completionPhoto) {
    form.append("completion_photo", completionPhoto);
  }

  const response = await api.put(
    `/returns/logistics/${returnId}/deliver-to-supplier`,
    form,
    { headers: { "Content-Type": undefined } },
  );
  return response.data.data;
}

export async function getCompletedHistory() {
  const response = await api.get("/logistics/history");
  return response.data.data || { delivered: [], returned: [] };
}
