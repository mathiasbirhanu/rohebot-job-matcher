import { apiClient } from "../client";

export type VerificationStatus = "Unverified" | "Pending Review" | "Verified" | "Rejected";
export type AvailabilityStatus = "Immediate" | "1 Week" | "1 Month" | "Not Available";
export type CandidateDocumentCategory =
  | "profilePhoto"
  | "educationCertificates"
  | "professionalLicenses"
  | "nationalIdFront"
  | "nationalIdBack"
  | "experienceLetter";

export interface CandidateDocument {
  id: string;
  category: CandidateDocumentCategory;
  name: string;
  contentType: string;
  sizeBytes: number;
  createdAt: string;
}

export interface CandidateDocumentUpload {
  category: CandidateDocumentCategory;
  file: File;
}

export interface CandidateProfile {
  id?: string;
  fullName: string;
  gender?: string;
  dateOfBirth?: string;
  profilePhotoUrl?: string;
  phone: string;
  email?: string;
  professionalCategory: string;
  qualificationLevel: string;
  educationBackground: string;
  certifications: string;
  yearsOfExperience: number;
  previousEmployment: string;
  professionalSummary: string;
  skills: string[];
  currentLocation: string;
  preferredLocation: string;
  employmentPreferences: string;
  availability: AvailabilityStatus;
  preferredWorkArrangement: "Full-time" | "Part-time" | "Contract" | "Shift Work";
  documents: CandidateDocument[];
  consentGiven: boolean;
  status: VerificationStatus;
}

export const candidateService = {
  submitProfile: async (profile: CandidateProfile): Promise<{ success: boolean }> => {
    return apiClient("/candidate/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    });
  },

  getMyProfile: async (): Promise<CandidateProfile> => {
    return apiClient("/candidate/profile");
  },

  uploadDocuments: async (uploads: CandidateDocumentUpload[]): Promise<CandidateDocument[]> => {
    const formData = new FormData();
    for (const upload of uploads) {
      formData.append("categories", upload.category);
      formData.append("files", upload.file, upload.file.name);
    }
    const result = await apiClient<{ documents: CandidateDocument[] }>("/candidate/documents", {
      method: "POST",
      body: formData,
    });
    return result.documents;
  },

  updateAvailability: async (availability: AvailabilityStatus): Promise<{ success: boolean }> => {
    return apiClient("/candidate/profile/availability", {
      method: "PATCH",
      body: JSON.stringify({ availability }),
    });
  }
}
