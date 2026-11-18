"use client";

import { Clock, CheckCircle2, Mail } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function EmployerPendingPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-8 shadow-sm text-center">
        <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <Clock className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Awaiting Admin Review</h1>
        <p className="text-slate-500 mb-6">
          Your organization profile and payment have been submitted. Rohobot admin will verify your documents and activate your account within 1-2 business days.
        </p>
        <div className="p-4 bg-slate-50 rounded-lg text-left mb-6">
          <p className="text-sm font-semibold text-slate-700 mb-2">What happens next?</p>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" /> Admin verifies your business license</li>
            <li className="flex items-start gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" /> Admin confirms your payment</li>
            <li className="flex items-start gap-2"><Mail className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" /> You receive an email once activated</li>
          </ul>
        </div>
        <Link href="/"><Button variant="outline" className="w-full">Back to Home</Button></Link>
      </div>
    </div>
  );
}