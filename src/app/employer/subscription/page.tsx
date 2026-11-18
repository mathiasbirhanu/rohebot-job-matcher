"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/Button";
import { paymentService, SUBSCRIPTION_PACKAGES, PackageTier, PaymentStatus } from "@/lib/api/services/payment";
import { CheckCircle2, CreditCard, Loader2, AlertTriangle } from "lucide-react";

export default function EmployerSubscriptionPage() {
  const [selectedTier, setSelectedTier] = useState<PackageTier | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | null>(null);
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const returnedTransactionId = query.get("transactionId");
    if (!returnedTransactionId) return;

    paymentService.verifyPaymentStatus(returnedTransactionId)
      .then((status) => {
        setTransactionId(returnedTransactionId);
        setPaymentStatus(status);
      })
      .catch((error: unknown) => {
        setTransactionId(returnedTransactionId);
        setErrorMessage(error instanceof Error ? error.message : "Could not verify payment status.");
      });
  }, []);

  const checkPaymentStatus = async () => {
    if (!transactionId) return;
    setIsProcessing(true);
    setErrorMessage("");
    try {
      setPaymentStatus(await paymentService.verifyPaymentStatus(transactionId));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not verify payment status.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSubscribe = async (tier: PackageTier) => {
    setSelectedTier(tier);
    setIsProcessing(true);
    setPaymentStatus(null);
    setErrorMessage("");
    try {
      const checkout = await paymentService.initiatePayment(tier);
      setTransactionId(checkout.transactionId);
      window.location.assign(checkout.checkoutUrl);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to start checkout.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <DashboardLayout role="employer">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900">Subscription &amp; Billing</h1>
          <p className="text-slate-500 text-sm mt-1">Choose a recruitment package and pay securely through Chapa.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SUBSCRIPTION_PACKAGES.map((pkg) => (
            <div
              key={pkg.tier}
              className={`relative bg-white border rounded-2xl p-6 flex flex-col transition-all ${
                selectedTier === pkg.tier ? "border-primary-500 ring-2 ring-primary-500 shadow-md" : "border-slate-200 shadow-sm hover:border-primary-200"
              }`}
            >
              {pkg.tier === "Gold" && (
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-gradient-to-r from-amber-400 to-amber-600 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
                  Most Popular
                </div>
              )}
              <div className="mb-6">
                <h3 className="text-lg font-bold text-slate-900">{pkg.tier}</h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-slate-900">{pkg.priceETB}</span>
                  <span className="text-sm text-slate-500">ETB / mo</span>
                </div>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {pkg.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm text-slate-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button
                variant={pkg.tier === "Gold" ? "primary" : "outline"}
                className="w-full"
                onClick={() => handleSubscribe(pkg.tier)}
                disabled={isProcessing}
              >
                {isProcessing && selectedTier === pkg.tier
                  ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  : <CreditCard className="w-4 h-4 mr-2" />}
                Select {pkg.tier}
              </Button>
            </div>
          ))}
        </div>

        {errorMessage && (
          <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 flex items-start gap-3" role="alert">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <p className="text-sm">{errorMessage}</p>
          </div>
        )}

        {paymentStatus && (
          <div className={`p-6 rounded-xl border flex items-start gap-4 ${
            paymentStatus === "Successful" ? "bg-emerald-50 border-emerald-200" :
            paymentStatus === "Pending" ? "bg-amber-50 border-amber-200" :
            "bg-red-50 border-red-200"
          }`} aria-live="polite">
            {paymentStatus === "Pending"
              ? <Loader2 className="w-6 h-6 text-amber-600 animate-spin" />
              : paymentStatus === "Successful"
                ? <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                : <AlertTriangle className="w-6 h-6 text-red-600" />}
            <div className="flex-1">
              <h3 className="font-semibold">Payment Status: {paymentStatus}</h3>
              <p className="text-sm mt-1">
                {paymentStatus === "Successful"
                  ? "The payment provider verified your transaction."
                  : paymentStatus === "Pending"
                    ? "The provider has not confirmed this payment yet."
                    : "The transaction was not completed. You can try again or contact support."}
              </p>
              {paymentStatus === "Pending" && (
                <Button variant="outline" size="sm" className="mt-3 bg-white" onClick={checkPaymentStatus} disabled={isProcessing}>
                  {isProcessing && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                  Check payment status
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
