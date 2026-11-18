"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Building2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient } from "@/lib/api/client";

const ORGANIZATION_TYPES = ["Hospital", "Clinic", "Home-Based Care", "Other"] as const;

interface EmployerProfile {
  organizationName: string;
  hrFirstName: string;
  hrMiddleName: string;
  hrLastName: string;
  organizationType: string;
  tinNumber: string;
  website: string;
  hrEmail: string;
  hrPhone: string;
  address: string;
  logoFileName: string;
  businessLicenseFileName: string;
  profileComplete: boolean;
}

export default function EmployerSetupPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<EmployerProfile>({
    organizationName: "",
    hrFirstName: "",
    hrMiddleName: "",
    hrLastName: "",
    organizationType: "",
    tinNumber: "",
    website: "",
    hrEmail: "",
    hrPhone: "",
    address: "",
    logoFileName: "",
    businessLicenseFileName: "",
    profileComplete: false,
  });
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [licenseFile, setLicenseFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiClient<EmployerProfile>("/employers/profile", { cache: "no-store" })
      .then(result => {
        if (active) setProfile(result);
      })
      .catch((loadError: unknown) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Could not load your employer profile.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, []);

  const updateProfile = (field: keyof EmployerProfile, value: string) => {
    setProfile(previous => ({ ...previous, [field]: value }));
  };

  const handleSaveProfile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if (!profile.profileComplete && !licenseFile) {
      setError("Upload your organization's business license to continue.");
      return;
    }
    if (licenseFile && licenseFile.size > 2 * 1024 * 1024) {
      setError("The business license file must be 2 MB or smaller.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient("/employers/profile", {
        method: "PUT",
        body: JSON.stringify({
          organizationName: profile.organizationName,
          organizationType: profile.organizationType,
          tinNumber: profile.tinNumber,
          website: profile.website,
          hrEmail: profile.hrEmail,
          hrPhone: profile.hrPhone,
          address: profile.address,
          logoFileName: logoFile?.name ?? profile.logoFileName,
          businessLicenseFileName: licenseFile?.name ?? profile.businessLicenseFileName,
        }),
      });
      router.push("/employer/packages");
    } catch (saveError: unknown) {
      setError(saveError instanceof Error ? saveError.message : "Could not save your profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <header className="mb-6 flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100 text-primary-700">
            <Building2 className="h-6 w-6" />
          </span>
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary-700">Employer account setup</p>
            <h1 className="text-2xl font-bold text-slate-900">Build your organization profile</h1>
          </div>
        </header>

        <p className="mb-6 text-sm text-slate-600">
          Your email is verified. Complete your organization details to continue.
        </p>
        {error && (
          <p role="alert" className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </p>
        )}

        {isLoading ? <p className="py-8 text-sm text-slate-600">Loading your account...</p> : (
          <form onSubmit={handleSaveProfile} className="space-y-5">
            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
              <span className="font-medium">HR Representative:</span>{" "}
              {[profile.hrFirstName, profile.hrMiddleName, profile.hrLastName].filter(Boolean).join(" ")}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-slate-700 sm:col-span-2">
                Organization Name *
                <input required value={profile.organizationName} onChange={event => updateProfile("organizationName", event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Organization Type *
                <select required value={profile.organizationType} onChange={event => updateProfile("organizationType", event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                  <option value="">Select type</option>
                  {ORGANIZATION_TYPES.map(type => <option key={type}>{type}</option>)}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700">
                TIN Number *
                <input required value={profile.tinNumber ?? ""} onChange={event => updateProfile("tinNumber", event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700 sm:col-span-2">
                Website (Optional)
                <input type="url" value={profile.website} onChange={event => updateProfile("website", event.target.value)} placeholder="https://" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                HR Email *
                <input required type="email" value={profile.hrEmail} onChange={event => updateProfile("hrEmail", event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                HR Phone *
                <input required type="tel" value={profile.hrPhone} onChange={event => updateProfile("hrPhone", event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700 sm:col-span-2">
                Organization Address *
                <input required value={profile.address} onChange={event => updateProfile("address", event.target.value)} placeholder="e.g. Bole, Addis Ababa" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">
                Organization Logo (Optional)
                <span className="mt-1 flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 p-3 text-sm font-normal text-slate-600">
                  <UploadCloud className="h-4 w-4 shrink-0" />
                  <span className="truncate">{logoFile?.name ?? profile.logoFileName ?? "Choose an image"}</span>
                  <input type="file" accept="image/*" className="sr-only" onChange={event => setLogoFile(event.target.files?.[0] ?? null)} />
                </span>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Business License *
                <span className="mt-1 flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 p-3 text-sm font-normal text-slate-600">
                  <UploadCloud className="h-4 w-4 shrink-0" />
                  <span className="truncate">{licenseFile?.name ?? profile.businessLicenseFileName ?? "PDF or image, max 2 MB"}</span>
                  <input type="file" accept=".pdf,image/png,image/jpeg,image/webp" className="sr-only" onChange={event => setLicenseFile(event.target.files?.[0] ?? null)} />
                </span>
              </label>
            </div>

            <Button type="submit" className="w-full" disabled={isLoading} isLoading={isSubmitting}>
              Save Organization Profile
            </Button>
          </form>
        )}
      </div>
    </main>
  );
}
