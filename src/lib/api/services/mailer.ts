import { apiClient } from "@/lib/api/client";

export type MailType =
  | "email_verification"
  | "training_invitation"
  | "profile_approved"
  | "profile_rejected"
  | "profile_review";

export interface SentMail {
  id: string;
  to: string;
  subject: string;
  body: string;
  link?: string;
  type: MailType;
  sentAt: string;
  opened: boolean;
  deliveryStatus?: "queued" | "sent" | "failed";
  attemptCount?: number;
  lastError?: string | null;
}

export const mailerService = {
  send: (mail: Omit<SentMail, "id" | "sentAt" | "opened" | "deliveryStatus" | "attemptCount" | "lastError">): Promise<SentMail> =>
    apiClient<SentMail>("/admin/email-outbox", {
      method: "POST",
      body: JSON.stringify(mail),
    }),

  getAll: (): Promise<SentMail[]> => apiClient("/admin/email-outbox"),

  markOpened: (id: string): Promise<{ success: boolean }> =>
    apiClient(`/admin/email-outbox/${encodeURIComponent(id)}`, { method: "PATCH" }),

  clear: (): Promise<void> => apiClient("/admin/email-outbox", { method: "DELETE" }),
};

// ========================================================
// EMAIL TEMPLATES
// ========================================================
export const emailTemplates = {
  verification: (firstName: string, verifyUrl: string) => ({
    subject: "Verify your Rohobot Training Account",
    body: `Hi ${firstName},\n\nPlease verify your email to start your Rohobot training.\n\nClick to verify:\n${verifyUrl}\n\nThis link expires in 24 hours.`,
    link: verifyUrl,
  }),

  trainingInvitation: (firstName: string, inviteUrl: string) => ({
    subject: "You've completed your training! Create your Rohobot profile",
    body: `Congratulations ${firstName}!\n\nYou've successfully completed the Rohobot training program.\n\nCreate your job matching profile:\n${inviteUrl}\n\nThis link is unique to you. Do not share it.`,
    link: inviteUrl,
  }),

  profileApproved: (firstName: string) => ({
    subject: "Your Rohobot Profile is Approved ✅",
    body: `Hello ${firstName},\n\nGreat news! Your profile has been reviewed and approved by the Rohobot admin team.\n\nYou are now visible to verified employers on the platform. You will start receiving interview invitations soon.\n\nLog in: ${typeof window !== "undefined" ? window.location.origin : ""}/candidate`,
    link: undefined,
  }),

  profileRejected: (firstName: string, reason: string) => ({
    subject: "Action Required: Your Rohobot Profile Needs Corrections",
    body: `Hello ${firstName},\n\nYour profile submission was reviewed but requires corrections:\n\n${reason}\n\nPlease log in to fix the issues and resubmit.`,
    link: undefined,
  }),
};