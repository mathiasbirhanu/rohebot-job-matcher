import { apiClient } from "../client";

export interface DashboardFilters {
  category?: string;
  location?: string;
}

export interface AggregatedMetrics {
  totalCandidates: number;
  verifiedCandidates: number;
  pendingVerifications: number;
  unavailableCandidates: number;
  genderSplit: { male: number; female: number };
  categorySplit: { name: string; value: number }[];
  locationSplit: { name: string; value: number }[];
  totalEmployers: number;
  verifiedEmployers: number;
  activeSubscriptions: { gold: number; silver: number; basic: number };
  totalRevenue: number;
  interviewsSent: number;
  interviewsAccepted: number;
  interviewsDeclined: number;
  interviewsCompleted: number;
  placementsCommenced: number;
  flaggedCandidates: number;
}

export const analyticsService = {
  getDashboardMetrics: (filters: DashboardFilters): Promise<AggregatedMetrics> => {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.location) params.set("location", filters.location);
    return apiClient(`/admin/analytics${params.size ? `?${params.toString()}` : ""}`);
  },
};
