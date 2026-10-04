import supplierApi from "./supplierApi";

export async function getNotifications() {
    const response = await supplierApi.get(
        "/notifications/"
    );

    return response.data.data ?? [];
}

export async function getUnreadNotificationCount() {
    const response = await supplierApi.get(
        "/notifications/unread-count"
    );

    return response.data.data?.count ?? 0;
}

export async function markNotificationRead(
    notificationId
) {
    const response = await supplierApi.put(
        `/notifications/${notificationId}/read`
    );

    return response.data;
}

export async function markAllNotificationsRead() {
    const response = await supplierApi.put(
        "/notifications/read-all"
    );

    return response.data;
}

export async function deleteNotification(
    notificationId
) {
    const response = await supplierApi.delete(
        `/notifications/${notificationId}`
    );

    return response.data;
}   