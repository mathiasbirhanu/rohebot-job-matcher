"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/Button";
import { organizationService, EmployerAccount, SUBSCRIPTION_PACKAGES } from "@/lib/api/services/organization";
import { Building2, CheckCircle2, XCircle, FileText, CreditCard, ChevronDown } from "lucide-react";

export default function AdminEmployerApprovalsPage() {
  const [employers, setEmployers] = useState<EmployerAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchEmployers = async () => {
    setIsLoading(true);
    const data = await organizationService.getAllEmployers();
    setEmployers(data);
    setIsLoading(false);
  };

  useEffect(() => { fetchEmployers(); }, []);

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    await organizationService.approveEmployer(id);
    await fetchEmployers();
    setProcessingId(null);
  };

  const handleReject = async (id: string) => {
    const reason = prompt("Reason for rejection:");
    if (!reason) return;
    setProcessingId(id);
    await organizationService.rejectEmployer(id, reason);
    await fetchEmployers();
    setProcessingId(null);
  };

  const pending = employers.filter(e => e.status === "Pending Admin Review");

  return (
    <DashboardLayout role="admin">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Building2 className="w-6 h-6 text-primary-600" /> Employer Approvals
          </h1>
          <p className="text-slate-500 text-sm mt-1">{pending.length} pending review</p>
        </div>

        <div className="space-y-3">
          {isLoading && <div className="p-8 text-center text-slate-500">Loading...</div>}

          {pending.map((emp) => {
            const pkg = SUBSCRIPTION_PACKAGES.find(p => p.tier === emp.subscriptionTier);
            return (
              <div key={emp.id} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div 
                  className="p-5 flex justify-between items-center cursor-pointer hover:bg-slate-50"
                  onClick={() => setExpandedId(expandedId === emp.id ? null : emp.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-primary-100 text-primary-700 rounded-lg flex items-center justify-center">
                      <Building2 className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900">{emp.organizationName || "Unnamed Org"}</h3>
                      <p className="text-sm text-slate-500">{emp.organizationType} • {emp.orgEmail}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="px-2.5 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full">{emp.subscriptionTier}</span>
                    <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${expandedId === emp.id ? "rotate-180" : ""}`} />
                  </div>
                </div>

                {expandedId === emp.id && (
                  <div className="border-t border-slate-100 p-5 bg-slate-50 grid grid-cols-1 md:grid-cols-2 gap-4 animate-in slide-in-from-top-2">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Organization</h4>
                      <p className="text-sm"><span className="text-slate-500">Name:</span> <strong>{emp.organizationName}</strong></p>
                      <p className="text-sm"><span className="text-slate-500">Type:</span> {emp.organizationType}</p>
                      <p className="text-sm"><span className="text-slate-500">TIN:</span> {emp.tinNumber}</p>
                      <p className="text-sm"><span className="text-slate-500">Address:</span> {emp.address}</p>
                      <p className="text-sm"><span className="text-slate-500">Website:</span> {emp.website || "-"}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">HR Contact</h4>
                      <p className="text-sm"><span className="text-slate-500">Name:</span> {emp.hrFirstName} {emp.hrLastName}</p>
                      <p className="text-sm"><span className="text-slate-500">Email:</span> {emp.hrEmail}</p>
                      <p className="text-sm"><span className="text-slate-500">Phone:</span> {emp.hrPhone}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1"><FileText className="w-3 h-3" /> Documents</h4>
                      <p className="text-sm"><span className="text-slate-500">License:</span> {emp.licenseDocumentName || "-"}</p>
                      <p className="text-sm"><span className="text-slate-500">Logo:</span> {emp.logoUrl || "-"}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1"><CreditCard className="w-3 h-3" /> Payment</h4>
                      <p className="text-sm"><span className="text-slate-500">Package:</span> {emp.subscriptionTier} ({pkg?.annualPayment != null ? `${pkg.annualPayment.toLocaleString()} ETB` : "Custom pricing"})</p>
                      <p className="text-sm"><span className="text-slate-500">Method:</span> {emp.paymentMethod}</p>
                      <p className="text-sm"><span className="text-slate-500">Reference:</span> <code className="text-xs bg-slate-200 px-1.5 py-0.5 rounded">{emp.transactionReference}</code></p>
                      <p className="text-sm"><span className="text-slate-500">Period:</span> {emp.subscriptionStartDate} → {emp.subscriptionEndDate}</p>
                    </div>

                    <div className="md:col-span-2 flex justify-end gap-2 pt-2">
                      <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => handleReject(emp.id)} isLoading={processingId === emp.id}>
                        <XCircle className="w-4 h-4 mr-1" /> Reject
                      </Button>
                      <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => handleApprove(emp.id)} isLoading={processingId === emp.id}>
                        <CheckCircle2 className="w-4 h-4 mr-1" /> Approve & Activate
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {!isLoading && pending.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <p className="text-slate-500">All employer accounts have been reviewed.</p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}