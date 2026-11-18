import { listRecords, updateRecord } from "../records";

export interface FlaggedCandidate {
  id: string;
  name: string;
  role: string;
  declineCount: number;
  lastDeclineDate: string;
  declineHistory: { employer: string; reason: string; date: string }[];
  flagStatus: "None" | "Flagged" | "Cleared" | "Investigated";
  adminNotes?: string;
}

export const declineMonitoringService = {
  getDeclineRecords: (): Promise<FlaggedCandidate[]> => listRecords("decline-records"),

  clearFlag: async (id: string, notes: string): Promise<{ success: boolean }> => {
    await updateRecord<FlaggedCandidate>("decline-records", id, {
      flagStatus: "Cleared",
      adminNotes: notes,
    });
    return { success: true };
  },

  annotateFlag: async (id: string, notes: string): Promise<{ success: boolean }> => {
    await updateRecord<FlaggedCandidate>("decline-records", id, {
      flagStatus: "Investigated",
      adminNotes: notes,
    });
    return { success: true };
  },
};
