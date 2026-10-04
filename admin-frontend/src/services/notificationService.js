import adminApi from "./api";

export async function getAdminNotifications() {
  const response = await adminApi.get("/admin/notifications", {
    params: { per_page: 50 },
  });
  return (
    response.data.data ?? { notifications: [], unread_count: 0, pagination: {} }
  );
}
export async function markAdminNotificationRead(notificationId) {
  const response = await adminApi.put(
    `/admin/notifications/${notificationId}/read`,
  );
  return response.data;
}
export async function markAllAdminNotificationsRead() {
  const response = await adminApi.put("/admin/notifications/read-all");
  return response.data;
}
export async function getAdminUnreadCount() {
  const response = await adminApi.get("/admin/notifications/unread-count");
  return response.data.data?.count ?? 0;
}

export async function deleteAdminNotification(id) {
  const response = await adminApi.delete(`/admin/notifications/${id}`);
  return response.data;
}
