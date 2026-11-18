"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/Button";
import { adminService, type AdminVerificationItem } from "@/lib/api/services/admin";
import { apiUrl } from "@/lib/api/client";
import { CheckCircle2, XCircle } from "lucide-react";

export default function AdminProfileApprovalsPage() {
  const [submissions, setSubmissions] = useState<AdminVerificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const loadSubmissions = async () => {
    const items = await adminService.getVerifications();
    setSubmissions(items.filter((item) => item.type === "Candidate"));
    setErrorMessage("");
  };

  useEffect(() => {
    let active = true;
    adminService.getVerifications()
      .then((items) => {
        if (active) setSubmissions(items.filter((item) => item.type === "Candidate"));
      })
      .catch((error: unknown) => {
        if (active) setErrorMessage(error instanceof Error ? error.message : "Could not load candidate profiles.");
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
    try {
      await adminService.updateVerificationStatus(item.id, status);
      await loadSubmissions();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update candidate profile.");
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <DashboardLayout role="admin">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Profile Approvals</h1>
          <p className="mt-1 text-sm text-slate-500">Review candidate profiles stored in the database.</p>
        </div>
        {errorMessage && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{errorMessage}</p>}

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {isLoading ? <div className="p-12 text-center text-slate-500">Loading...</div> : (
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-medium">Candidate</th>
                  <th className="px-6 py-3 font-medium">Category</th>
                  <th className="px-6 py-3 font-medium">Documents</th>
                  <th className="px-6 py-3 font-medium">Submitted</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {submissions.map((submission) => (
                  <tr key={submission.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-medium text-slate-900">{submission.name}</td>
                    <td className="px-6 py-4 text-slate-600">{submission.roleOrCategory || "—"}</td>
                    <td className="px-6 py-4 text-slate-600">
                      {submission.documents?.length ? (
                        <ul className="space-y-1">
                          {submission.documents.map((document) => (
                            <li key={document.id}>
                              <a
                                href={apiUrl(`/admin/candidates/${encodeURIComponent(submission.id.split(":")[1])}/documents/${encodeURIComponent(document.id)}`)}
                                target="_blank"
                                rel="noreferrer"
                                className="text-primary-700 hover:underline"
                              >
                                {document.name}
                              </a>
                            </li>
                          ))}
                        </ul>
                      ) : "No files"}
                    </td>
                    <td className="px-6 py-4 text-slate-500">{submission.submittedDate || "—"}</td>
                    <td className="px-6 py-4">{submission.status}</td>
                    <td className="px-6 py-4 text-right">
                      {submission.status === "Pending" && (
                        <div className="flex justify-end gap-2">
                          <Button type="button" size="sm" variant="outline" className="border-emerald-200 text-emerald-700" disabled={processingId !== null} isLoading={processingId === submission.id} onClick={() => review(submission, "Approved")}>
                            <CheckCircle2 className="mr-1 h-3 w-3" /> Approve
                          </Button>
                          <Button type="button" size="sm" variant="outline" className="border-red-200 text-red-700" disabled={processingId !== null} onClick={() => review(submission, "Rejected")}>
                            <XCircle className="mr-1 h-3 w-3" /> Reject
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {!submissions.length && <tr><td className="px-6 py-8 text-center text-slate-500" colSpan={6}>No candidate profiles found.</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
