import { createRecord, listRecords } from "../records";

export type RecruitmentOutcome = "Shortlisted" | "Selected" | "Unsuccessful" | "Pending";

export interface EmployerFeedback {
  id: string;
  interviewId: string;
  candidateId: string;
  candidateName: string;
  employerName: string;
  positionTitle: string;
  interviewDate: string;
  professionalKnowledge: number;
  communicationSkills: number;
  relevantExperience: number;
  overallSuitability: number;
  outcome: RecruitmentOutcome;
  additionalComments: string;
  submittedAt: string;
  submittedBy: string;
}

export const feedbackService = {
  submitFeedback: async (
    feedback: Omit<EmployerFeedback, "id" | "submittedAt">
  ): Promise<{ success: boolean }> => {
    await createRecord("feedback", {
      ...feedback,
      submittedAt: new Date().toISOString(),
    });
    return { success: true };
  },

  checkIfFeedbackSubmitted: async (interviewId: string): Promise<boolean> => {
    const feedback = await listRecords<EmployerFeedback>("feedback");
    return feedback.some((item) => item.interviewId === interviewId);
  },

  getAllFeedback: (): Promise<EmployerFeedback[]> => listRecords("feedback"),
};
