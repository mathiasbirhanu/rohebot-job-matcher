import { apiClient } from "../client";

export type OrganizationType = "Hospital" | "Clinic" | "Home-Based Care" | "Other";
export type PackageTier = "Basic" | "Silver" | "Gold" | "Premium";
export type PaymentMethod = "Telebirr" | "CBE" | "Dashen" | "Abyssinia" | "Awash" | "Other";
export type AccountStatus = "Pending OTP" | "OTP Verified" | "Profile Incomplete" | "Pending Admin Review" | "Active" | "Rejected";

export interface SubscriptionPackage {
  tier: PackageTier;
  annualCapacity: number | "Unlimited";
  discount: number;
  costPerTrainee: number;
  annualPayment: number | null;
}

export const SUBSCRIPTION_PACKAGES: SubscriptionPackage[] = [
  { tier: "Basic", annualCapacity: 50, discount: 10, costPerTrainee: 2731.5, annualPayment: 136575 },
  { tier: "Silver", annualCapacity: 150, discount: 15, costPerTrainee: 2579.75, annualPayment: 386962.5 },
  { tier: "Gold", annualCapacity: 500, discount: 20, costPerTrainee: 2428, annualPayment: 1214000 },
  { tier: "Premium", annualCapacity: "Unlimited", discount: 25, costPerTrainee: 2276.25, annualPayment: null },
];

export interface EmployerAccount {
  id: string;
  hrFirstName: string;
  hrMiddleName: string;
  hrLastName: string;
  orgEmail: string;
  orgPhone: string;
  otpCode?: string;
  otpVerified: boolean;
  logoUrl?: string;
  organizationName?: string;
  organizationType?: OrganizationType;
  tinNumber?: string;
  licenseDocumentName?: string;
  website?: string;
  hrEmail?: string;
  hrPhone?: string;
  address?: string;
  subscriptionTier?: PackageTier;
  subscriptionStartDate?: string;
  subscriptionEndDate?: string;
  paymentMethod?: PaymentMethod;
  paymentAccountUsed?: string;
  transactionReference?: string;
  paymentProofName?: string;
  paymentSubmitted: boolean;
  status: AccountStatus;
  rejectionReason?: string;
  createdAt: string;
}

export interface OrganizationProfile {
  name: string;
  type: string;
  location: string;
  status: AccountStatus;
  contactEmail: string;
  contactPhone: string;
  representativeName: string;
  representativePhone: string;
  licenseDocumentName: string;
  subscriptionTier: PackageTier | null;
}

interface EmployerApiProfile {
  id: string;
  organizationName: string;
  organizationType?: OrganizationType;
  city?: string;
  website?: string;
  status: AccountStatus;
  hrFirstName?: string;
  hrMiddleName?: string;
  hrLastName?: string;
  orgEmail?: string;
  orgPhone?: string;
  hrEmail?: string;
  hrPhone?: string;
  tinNumber?: string;
  licenseDocumentName?: string;
  paymentSubmitted?: boolean;
  subscriptionTier?: PackageTier;
  subscriptionEndDate?: string;
  rejectionReason?: string;
  createdAt?: string;
  address?: string;
}

function toEmployerAccount(profile: EmployerApiProfile): EmployerAccount {
  return {
    id: profile.id,
    hrFirstName: profile.hrFirstName ?? "",
    hrMiddleName: profile.hrMiddleName ?? "",
    hrLastName: profile.hrLastName ?? "",
    orgEmail: profile.orgEmail ?? profile.hrEmail ?? "",
    orgPhone: profile.orgPhone ?? profile.hrPhone ?? "",
    otpVerified: profile.status !== "Pending OTP",
    organizationName: profile.organizationName,
    organizationType: profile.organizationType,
    tinNumber: profile.tinNumber,
    licenseDocumentName: profile.licenseDocumentName,
    website: profile.website,
    hrEmail: profile.hrEmail,
    hrPhone: profile.hrPhone,
    address: profile.address ?? profile.city,
    subscriptionTier: profile.subscriptionTier,
    subscriptionEndDate: profile.subscriptionEndDate,
    paymentSubmitted: Boolean(profile.paymentSubmitted),
    status: profile.status,
    rejectionReason: profile.rejectionReason,
    createdAt: profile.createdAt ?? "",
  };
}

export const organizationService = {
  signup: (data: {
    hrFirstName: string;
    hrMiddleName: string;
    hrLastName: string;
    orgEmail: string;
    orgPhone: string;
    password: string;
    organizationName?: string;
  }): Promise<{ success: boolean; employerId: string; message: string; testOtp?: string }> =>
    apiClient<{ success: boolean; userId: string; message: string; testOtp?: string }>(
      "/auth/register/employer",
      {
        method: "POST",
        body: JSON.stringify({
          email: data.orgEmail,
          phone: data.orgPhone,
          password: data.password,
          organization_name: data.organizationName ?? "New Organization",
          hr_first_name: data.hrFirstName,
          hr_middle_name: data.hrMiddleName,
          hr_last_name: data.hrLastName,
        }),
      }
    ).then((result) => ({
      success: result.success,
      employerId: result.userId,
      message: result.message,
      ...(result.testOtp ? { testOtp: result.testOtp } : {}),
    })),

  verifyOTP: async (employerId: string, otpCode: string): Promise<{ success: boolean }> => {
    const params = new URLSearchParams({ user_id: employerId, code: otpCode });
    return apiClient(`/auth/verify-email?${params.toString()}`, { method: "POST" });
  },

  saveOrganizationProfile: (
    _employerId: string,
    profile: {
      logoUrl?: string;
      organizationName: string;
      organizationType: OrganizationType;
      tinNumber: string;
      licenseDocumentName: string;
      website?: string;
      hrEmail: string;
      hrPhone: string;
      address: string;
    }
  ): Promise<{ success: boolean }> =>
    apiClient("/employers/profile", { method: "PUT", body: JSON.stringify(profile) }),

  submitSubscription: (
    _employerId: string,
    data: {
      subscriptionTier: PackageTier;
      paymentMethod: PaymentMethod;
      paymentAccountUsed: string;
      transactionReference: string;
      paymentProofName?: string;
    }
  ): Promise<{ success: boolean }> =>
    apiClient("/employers/subscription", { method: "POST", body: JSON.stringify(data) }),

  getAllEmployers: async (): Promise<EmployerAccount[]> =>
    (await apiClient<EmployerApiProfile[]>("/admin/employers")).map(toEmployerAccount),

  getEmployerById: async (id: string): Promise<EmployerAccount | null> =>
    (await organizationService.getAllEmployers()).find((employer) => employer.id === id) ?? null,

  getCurrentEmployer: async (): Promise<EmployerAccount | null> => {
    try {
      return toEmployerAccount(await apiClient<EmployerApiProfile>("/employers/profile"));
    } catch (error) {
      if (error instanceof Error && "status" in error && error.status === 404) return null;
      throw error;
    }
  },

  getOrganizationProfile: async (): Promise<OrganizationProfile> => {
    const profile = await apiClient<EmployerApiProfile>("/employers/profile");
    return {
      name: profile.organizationName,
      type: profile.organizationType ?? "Not provided",
      location: profile.address ?? profile.city ?? "Not provided",
      status: profile.status,
      contactEmail: profile.hrEmail ?? profile.orgEmail ?? "",
      contactPhone: profile.hrPhone ?? profile.orgPhone ?? "",
      representativeName: [profile.hrFirstName, profile.hrMiddleName, profile.hrLastName]
        .filter(Boolean)
        .join(" "),
      representativePhone: profile.hrPhone ?? profile.orgPhone ?? "",
      licenseDocumentName: profile.licenseDocumentName ?? "No license uploaded",
      subscriptionTier: profile.subscriptionTier ?? null,
    };
  },

  approveEmployer: (employerId: string): Promise<{ success: boolean }> =>
    apiClient(`/admin/employers/${encodeURIComponent(employerId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "Active" }),
    }),

  rejectEmployer: (employerId: string, reason: string): Promise<{ success: boolean }> =>
    apiClient(`/admin/employers/${encodeURIComponent(employerId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "Rejected", reason }),
    }),

  getSubscriptionDaysLeft: (employer: EmployerAccount): number => {
    if (!employer.subscriptionEndDate) return 0;
    const end = new Date(employer.subscriptionEndDate);
    return Math.max(0, Math.ceil((end.getTime() - Date.now()) / 86_400_000));
  },
};
