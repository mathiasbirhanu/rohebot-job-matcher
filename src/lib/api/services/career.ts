import { createRecord, listRecords } from "../records";

export interface TrainingResource {
  id: string;
  title: string;
  provider: string;
  duration: string;
  category: string;
  description: string;
  isRohobotOfficial: boolean;
}

export interface CandidateCertificate {
  id: string;
  courseName: string;
  issueDate: string;
  certificateUrl: string;
  status: "Completed" | "In Progress";
}

export interface SkillsGap {
  skillName: string;
  reason: string;
  recommendedCourseId: string;
}

export const careerService = {
  getTrainingResources: (): Promise<TrainingResource[]> => listRecords("courses"),

  getMyCertificates: (): Promise<CandidateCertificate[]> => listRecords("certificates"),

  enrollInCourse: async (courseId: string): Promise<{ success: boolean }> => {
    await createRecord("career-enrollments", { courseId });
    return { success: true };
  },

  getSkillsGapRecommendations: (): Promise<SkillsGap[]> => listRecords("skills-gap"),
};
