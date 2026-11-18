import { createRecord, listRecords, updateRecord } from "../records";

export type NotificationType = "info" | "success" | "warning" | "error";

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  isRead: boolean;
  type: NotificationType;
  targetRole: "candidate" | "employer" | "admin";
}

export const notificationService = {
  getNotifications: async (
    _role: "candidate" | "employer" | "admin"
  ): Promise<AppNotification[]> => listRecords("notifications"),

  markAsRead: async (id: string): Promise<void> => {
    await updateRecord("notifications", id, { isRead: true });
  },

  markAllAsRead: async (_role: string): Promise<void> => {
    const notifications = await listRecords<AppNotification>("notifications");
    await Promise.all(
      notifications
        .filter((notification) => !notification.isRead)
        .map((notification) => updateRecord("notifications", notification.id, { isRead: true }))
    );
  },

  pushNotification: (
    title: string,
    message: string,
    type: NotificationType,
    targetRole: "candidate" | "employer" | "admin"
  ): Promise<AppNotification> =>
    createRecord("notifications", {
      title,
      message,
      type,
      targetRole,
      timestamp: new Date().toISOString(),
      isRead: false,
    }),
};
