import { apiClient } from "../client";

export interface TrainerInvitation {
  id: string;
  fullName: string;
  email: string;
  emailVerified: boolean;
  trainingCompleted: boolean;
  invitationSent: boolean;
  profileCreated: boolean;
  registeredAt: string;
}

export interface TrainerQrSettings {
  active: boolean;
  expiresAt: string | null;
}

export interface TrainerQrDisplaySettings extends TrainerQrSettings {
  registrationUrl: string;
}

export interface TrainerInvitationDetails {
  fullName: string;
  email: string;
}

export const trainingService = {
  getQrSettings: (): Promise<TrainerQrDisplaySettings> =>
    apiClient("/training?view=scan", { cache: "no-store" }),

  saveQrSettings: async (settings: TrainerQrSettings): Promise<TrainerQrSettings> => {
    const result = await apiClient<{ success: boolean; settings?: TrainerQrSettings; message?: string }>(
      "/training",
      { method: "PATCH", body: JSON.stringify(settings) }
    );
    if (!result.success || !result.settings) {
      throw new Error(result.message ?? "Could not save QR settings.");
    }
    return result.settings;
  },

  registerTrainerFromQR: (data: {
    firstName: string;
    middleName: string;
    lastName: string;
    email: string;
  }) =>
    apiClient<{ success: boolean; message: string; verificationLink?: string }>("/training", {
      method: "POST",
      body: JSON.stringify({ action: "register", ...data }),
    }),

  verifyTrainerEmail: (token: string) => {
    const params = new URLSearchParams({ token });
    return apiClient<{ success: boolean; message: string }>(
      `/training/verify?${params.toString()}`,
      { method: "POST" }
    );
  },

  getAllTrainers: async (): Promise<TrainerInvitation[]> => {
    const result = await apiClient<{ trainers: TrainerInvitation[] }>("/training", {
      cache: "no-store",
    });
    return result.trainers;
  },

  markTrainingComplete: (trainerId: string) =>
    apiClient<{ success: boolean; message: string; invitationLink: string }>("/training", {
      method: "POST",
      body: JSON.stringify({ action: "complete", trainerId }),
    }),

  getTrainerByToken: async (token: string): Promise<TrainerInvitationDetails | null> => {
    const result = await apiClient<{
      valid: boolean;
      fullName?: string;
      email?: string;
      message?: string;
    }>("/training", {
      method: "POST",
      body: JSON.stringify({ action: "inspect", token }),
    });
    if (!result.valid || !result.fullName || !result.email) return null;
    return { fullName: result.fullName, email: result.email };
  },

  completeSignup: (token: string, phone: string, password: string) =>
    apiClient<{ success: boolean; message: string }>("/training", {
      method: "POST",
      body: JSON.stringify({ action: "signup", token, phone, password }),
    }),
};
