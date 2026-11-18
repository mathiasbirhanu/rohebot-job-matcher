"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/Button";
import { adminService, type AdminVerificationItem } from "@/lib/api/services/admin";

export default function AdminWorkflowReviewsPage() {
  const [verifications, setVerifications] = useState<AdminVerificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const loadVerifications = useCallback(async () => {
    const items = await adminService.getVerifications();
    setVerifications(items);
    setErrorMessage("");
  }, []);

  useEffect(() => {
    let active = true;
    adminService.getVerifications()
      .then((items) => {
        if (active) setVerifications(items);
      })
      .catch((error: unknown) => {
        if (active) setErrorMessage(error instanceof Error ? error.message : "Could not load verifications.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const review = async (item: AdminVerificationItem, status: "Approved" | "Rejected") => {
    setProcessingId(item.id);
    setErrorMessage("");
    setNotice("");
    try {
      await adminService.updateVerificationStatus(item.id, status);
      await loadVerifications();
      setNotice(`${item.type} ${status.toLowerCase()}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update verification.");
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <DashboardLayout role="admin">
      <div className="mx-auto max-w-5xl space-y-6">
        <header>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary-700">Admin tools</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Workflow reviews</h1>
          <p className="mt-2 text-sm text-slate-600">Review candidate and employer accounts stored in the database.</p>
        </header>

        <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Verification codes are recorded in the local email outbox. Open the Dev Inbox to review local email records.
        </div>
        {errorMessage && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{errorMessage}</p>}
        {notice && <p role="status" className="rounded-xl border border-primary-200 bg-primary-50 p-4 text-sm text-primary-800">{notice}</p>}

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                <ShieldCheck className="h-5 w-5 text-primary-700" /> Account verifications
              </h2>
              <p className="mt-1 text-sm text-slate-500">Approve or reject submitted candidate and employer accounts.</p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => {
                setIsLoading(true);
                loadVerifications()
                  .catch((error: unknown) => setErrorMessage(error instanceof Error ? error.message : "Could not refresh."))
                  .finally(() => setIsLoading(false));
              }}
            >
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </div>
          {isLoading ? <p className="py-6 text-sm text-slate-500">Loading...</p> : verifications.length ? (
            <ul className="divide-y divide-slate-100">
              {verifications.map((item) => (
                <li key={item.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium text-slate-900">{item.name} <span className="font-normal text-slate-500">({item.type})</span></p>
                    <p className="text-sm text-slate-600">{item.roleOrCategory || "No category provided"}</p>
                    <p className="text-xs text-slate-500">Submitted {item.submittedDate || "date unavailable"}</p>
                    <p className="mt-1 text-xs font-medium text-slate-700">Status: {item.status}</p>
                  </div>
                  {item.status === "Pending" && (
                    <div className="flex gap-2">
                      <Button type="button" size="sm" className="gap-1" disabled={processingId !== null} isLoading={processingId === item.id} onClick={() => review(item, "Approved")}>
                        <CheckCircle2 className="h-4 w-4" /> Approve
                      </Button>
                      <Button type="button" size="sm" variant="outline" className="gap-1 text-red-700" disabled={processingId !== null} onClick={() => review(item, "Rejected")}>
                        <XCircle className="h-4 w-4" /> Reject
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : <p className="py-6 text-sm text-slate-500">No accounts are waiting for review.</p>}
        </section>
      </div>
    </DashboardLayout>
  );
}
