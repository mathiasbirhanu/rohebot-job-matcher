import { apiClient } from "../client";
import { listRecords, updateRecord } from "../records";
import type { CandidateDocument } from "./candidate";

export type VerificationStatus = "Pending" | "Approved" | "Rejected" | "Unverified";
export type EntityType = "Candidate" | "Employer";

export interface AdminVerificationItem {
  id: string;
  name: string;
  type: EntityType;
  roleOrCategory: string;
  submittedDate: string;
  status: VerificationStatus;
  documents?: CandidateDocument[];
}

export interface Transaction {
  id: string;
  referenceNumber: string;
  employerName: string;
  packageTier: "Basic" | "Silver" | "Gold";
  amount: number;
  date: string;
  status: "Successful" | "Pending" | "Failed" | "Refunded";
}

export interface AuditLog {
  id: string;
  employerName: string;
  searchQuery: string;
  filtersUsed: string;
  timestamp: string;
  resultsCount: number;
}

export const adminService = {
  getVerifications: (): Promise<AdminVerificationItem[]> => apiClient("/admin/verifications"),

  updateVerificationStatus: async (
    id: string,
    status: "Approved" | "Rejected"
  ): Promise<{ success: boolean }> =>
    apiClient(`/admin/verifications/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  getTransactions: (): Promise<Transaction[]> => listRecords("transactions"),

  refundTransaction: async (id: string): Promise<{ success: boolean }> => {
    await updateRecord<Transaction>("transactions", id, { status: "Refunded" });
    return { success: true };
  },

  approvePendingPayment: async (id: string): Promise<{ success: boolean }> => {
    await updateRecord<Transaction>("transactions", id, { status: "Successful" });
    return { success: true };
  },

  getAuditLogs: async (): Promise<AuditLog[]> => {
    const records = await listRecords<Omit<AuditLog, "filtersUsed"> & { filtersUsed: string[] }>(
      "audit-logs"
    );
    return records.map((record) => ({ ...record, filtersUsed: record.filtersUsed.join(", ") }));
  },
};
