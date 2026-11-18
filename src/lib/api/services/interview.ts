import { createRecord, listRecords, updateRecord } from "../records";

export type InterviewStatus = "Pending" | "Accepted" | "Declined" | "Rescheduling Requested" | "Completed";

export interface InterviewRequest {
  id: string;
  candidateId: string;
  candidateName: string;
  employerName: string;
  positionTitle: string;
  date: string;
  time: string;
  location: string;
  notes?: string;
  status: InterviewStatus;
  rescheduleReason?: string;
  proposedNewDate?: string;
  declineReason?: string;
}

export const interviewService = {
  getCandidateInterviews: (): Promise<InterviewRequest[]> => listRecords("interviews"),

  respondToInterview: async (
    id: string,
    status: "Accepted" | "Declined",
    reason?: string
  ): Promise<{ success: boolean }> => {
    await updateRecord<InterviewRequest>("interviews", id, {
      status,
      ...(status === "Declined" ? { declineReason: reason } : {}),
    });
    return { success: true };
  },

  requestReschedule: async (
    id: string,
    reason: string,
    newDate: string
  ): Promise<{ success: boolean }> => {
    await updateRecord<InterviewRequest>("interviews", id, {
      status: "Rescheduling Requested",
      rescheduleReason: reason,
      proposedNewDate: newDate,
    });
    return { success: true };
  },

  getEmployerInterviews: (): Promise<InterviewRequest[]> => listRecords("interviews"),

  createRequest: async (
    data: Omit<InterviewRequest, "id" | "status">
  ): Promise<{ success: boolean }> => {
    await createRecord<InterviewRequest>("interviews", { ...data, status: "Pending" });
    return { success: true };
  },

  markAsCompleted: async (id: string): Promise<{ success: boolean }> => {
    await updateRecord<InterviewRequest>("interviews", id, { status: "Completed" });
    return { success: true };
  },
};
