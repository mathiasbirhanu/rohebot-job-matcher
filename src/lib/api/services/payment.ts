import { apiClient } from "../client";
import { listRecords } from "../records";

export type PackageTier = "Basic" | "Silver" | "Gold";
export type PaymentStatus = "Pending" | "Successful" | "Failed" | "Refunded" | "Disputed";

export interface SubscriptionPackage {
  tier: PackageTier;
  priceETB: number;
  durationMonths: number;
  candidateViewLimit: number | "Unlimited";
  interviewRequestLimit: number | "Unlimited";
  features: string[];
}

export interface Transaction {
  id: string;
  referenceNumber: string;
  employerName: string;
  packageTier: PackageTier;
  amount: number;
  date: string;
  status: PaymentStatus;
}

export const SUBSCRIPTION_PACKAGES: SubscriptionPackage[] = [
  { tier: "Basic", priceETB: 500, durationMonths: 1, candidateViewLimit: 10, interviewRequestLimit: 3, features: ["10 Candidate Profile Views", "3 Interview Requests / mo", "Standard Support"] },
  { tier: "Silver", priceETB: 1500, durationMonths: 1, candidateViewLimit: 50, interviewRequestLimit: 15, features: ["50 Candidate Profile Views", "15 Interview Requests / mo", "Priority Support", "Standard Verification"] },
  { tier: "Gold", priceETB: 3000, durationMonths: 1, candidateViewLimit: "Unlimited", interviewRequestLimit: "Unlimited", features: ["Unlimited Candidate Views", "Unlimited Interview Requests", "Dedicated Account Manager", "Featured Employer Badge"] },
];

export const paymentService = {
  initiatePayment: (tier: PackageTier): Promise<{ checkoutUrl: string; transactionId: string }> =>
    apiClient("/payments/chapa/checkout", {
      method: "POST",
      body: JSON.stringify({ packageTier: tier }),
    }),

  verifyPaymentStatus: async (transactionId: string): Promise<PaymentStatus> => {
    const result = await apiClient<{ status: PaymentStatus }>(
      `/payments/transactions/${encodeURIComponent(transactionId)}`
    );
    return result.status;
  },

  getAllTransactions: (): Promise<Transaction[]> => listRecords("transactions"),
};
