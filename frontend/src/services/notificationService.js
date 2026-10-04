import api from "./api";

export async function getNotifications() {
  const response = await api.get("/notifications/");
  return response.data.data || [];
}

export async function markNotificationRead(notificationId) {
  const response = await api.put(`/notifications/${notificationId}/read`);
  return response.data;
}

export async function markAllNotificationsRead() {
  const response = await api.put("/notifications/read-all");
  return response.data;
}

export async function deleteNotification(notificationId) {
  const response = await api.delete(`/notifications/${notificationId}`);
  return response.data;
}

export async function getUnreadNotificationCount() {
  const response = await api.get("/notifications/unread-count");
  return Number(response.data.data?.count || 0);
}
