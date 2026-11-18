import { listRecords, updateRecord } from "../records";

export type PlacementStage =
  | "Matched"
  | "Interviewed"
  | "Selected"
  | "Offer Accepted"
  | "Commenced Employment"
  | "Discontinued";

export interface PlacementRecord {
  id: string;
  candidateId: string;
  candidateName: string;
  employerName: string;
  positionTitle: string;
  location: string;
  stage: PlacementStage;
  interviewDate?: string;
  selectionDate?: string;
  offerAcceptedDate?: string;
  employmentStartDate?: string;
  followUpDate?: string;
  employerConfirmed: boolean;
  candidateConfirmed: boolean;
  unsuccessfulReason?: string;
  discontinuationReason?: string;
  lastUpdated: string;
}

export const placementService = {
  getEmployerPlacements: (): Promise<PlacementRecord[]> => listRecords("placements"),

  confirmSelection: async (
    id: string,
    startDate: string
  ): Promise<{ success: boolean }> => {
    await updateRecord<PlacementRecord>("placements", id, {
      stage: "Selected",
      employmentStartDate: startDate,
      employerConfirmed: true,
      lastUpdated: new Date().toISOString(),
    });
    return { success: true };
  },

  confirmEmployment: async (id: string): Promise<{ success: boolean }> => {
    await updateRecord<PlacementRecord>("placements", id, {
      stage: "Commenced Employment",
      candidateConfirmed: true,
      lastUpdated: new Date().toISOString(),
    });
    return { success: true };
  },

  getAllPlacements: (): Promise<PlacementRecord[]> => listRecords("placements"),
};
