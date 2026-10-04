import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FiBell, FiCheck, FiTrash2 } from "react-icons/fi";
import Container from "../../components/common/Container";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/common/AsyncState";
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../services/notificationService";
import { formatDateTime } from "../../utils/formatters";
import { getApiMessage } from "../../utils/apiError";

export default function Notifications() {
  const client = useQueryClient();
  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
  });
  const [message, setMessage] = useState("");

  const mutation = useMutation({
    mutationFn: async ({ type, id }) => {
      if (type === "read") return markNotificationRead(id);
      if (type === "delete") return deleteNotification(id);
      return markAllNotificationsRead();
    },
    onSuccess: (_, variables) => {
      if (variables.type === "read") {
        client.setQueryData(["notifications"], (current = []) =>
          current.map((item) =>
            item.id === variables.id ? { ...item, is_read: true } : item,
          ),
        );
      } else if (variables.type === "delete") {
        client.setQueryData(["notifications"], (current = []) =>
          current.filter((item) => item.id !== variables.id),
        );
      } else {
        client.setQueryData(["notifications"], (current = []) =>
          current.map((item) => ({ ...item, is_read: true })),
        );
      }
      client.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
    onError: (error) =>
      setMessage(getApiMessage(error, "Couldn't update notifications.")),
  });

  if (notificationsQuery.isLoading)
    return (
      <div className="cc-page-shell">
        <Container>
          <LoadingState label="Loading notifications…" />
        </Container>
      </div>
    );
  if (notificationsQuery.isError)
    return (
      <div className="cc-page-shell">
        <Container>
          <ErrorState
            message="We couldn't load your notifications."
            onRetry={() => notificationsQuery.refetch()}
          />
        </Container>
      </div>
    );

  const notifications = notificationsQuery.data || [];
  const unread = notifications.filter((item) => !item.is_read).length;

  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-page-heading">
          <div>
            <span className="cc-eyebrow">Account activity</span>
            <h1>Notifications</h1>
            <p>
              {unread
                ? `${unread} unread notification${unread !== 1 ? "s" : ""}`
                : "You're all caught up."}
            </p>
          </div>
          {unread ? (
            <button
              type="button"
              className="cc-btn secondary"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate({ type: "all" })}
            >
              <FiCheck /> Mark all read
            </button>
          ) : null}
        </div>
        {message ? (
          <div className="cc-form-error" role="alert">
            {message}
          </div>
        ) : null}
        {!notifications.length ? (
          <EmptyState
            icon={<FiBell />}
            title="No notifications"
            message="Order and account updates will appear here."
          />
        ) : (
          <div className="cc-notification-list">
            {notifications.map((notification) => (
              <article
                key={notification.id}
                className={`cc-notification${notification.is_read ? " read" : ""}`}
              >
                <div className="cc-notification-icon">
                  <FiBell />
                </div>
                <div className="cc-notification-body">
                  <div>
                    <strong>{notification.title}</strong>
                    {!notification.is_read ? (
                      <span className="cc-unread-dot" title="Unread" />
                    ) : null}
                  </div>
                  <p>{notification.message}</p>
                  <small>{formatDateTime(notification.created_at)}</small>
                </div>
                <div className="cc-notification-actions">
                  {!notification.is_read ? (
                    <button
                      type="button"
                      disabled={mutation.isPending}
                      onClick={() =>
                        mutation.mutate({ type: "read", id: notification.id })
                      }
                    >
                      <FiCheck /> Read
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="danger"
                    disabled={mutation.isPending}
                    onClick={() =>
                      mutation.mutate({ type: "delete", id: notification.id })
                    }
                  >
                    <FiTrash2 /> Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </Container>
    </div>
  );
}
