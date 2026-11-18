import { apiClient } from "../client";
import type { AvailabilityStatus, CandidateProfile } from "./candidate";

type WorkArrangement = CandidateProfile["preferredWorkArrangement"];

export interface SearchCriteria {
  query: string;
  category: string;
  qualification: string;
  location: string;
  minExperience: number;
  availability: AvailabilityStatus | "";
  workArrangement: WorkArrangement | "";
}

export interface MatchReason {
  label: string;
  type: "positive" | "neutral";
}

export interface MatchedCandidate {
  id: string;
  name: string;
  role: string;
  qualification: string;
  experienceYears: number;
  location: string;
  professionalSummary: string;
  skills: string[];
  availability: AvailabilityStatus;
  workArrangement: WorkArrangement;
  isVerified: boolean;
  isActive: boolean;
  matchScore: number;
  matchReasons: MatchReason[];
  isSaved: boolean;
}

export interface MatchingConfig {
  immediateAvailabilityBoost: number;
  highExperienceBoost: number;
  locationMatchBoost: number;
  minExperienceWeight: number;
}

export const DEFAULT_MATCHING_CONFIG: MatchingConfig = {
  immediateAvailabilityBoost: 20,
  highExperienceBoost: 15,
  locationMatchBoost: 15,
  minExperienceWeight: 1,
};

export const employerService = {
  searchCandidates: async (
    criteria: SearchCriteria,
    _config: MatchingConfig = DEFAULT_MATCHING_CONFIG
  ): Promise<MatchedCandidate[]> => {
    const params = new URLSearchParams({
      query: criteria.query,
      category: criteria.category,
      qualification: criteria.qualification,
      location: criteria.location,
      min_experience: String(criteria.minExperience),
      availability: criteria.availability,
      work_arrangement: criteria.workArrangement,
    });
    return apiClient(`/employers/search-candidates?${params.toString()}`);
  },

  toggleSaveCandidate: async (candidateId: string): Promise<boolean> => {
    const result = await apiClient<{ saved: boolean }>(
      `/employers/saved-candidates/${encodeURIComponent(candidateId)}`,
      { method: "POST" }
    );
    return result.saved;
  },
};
