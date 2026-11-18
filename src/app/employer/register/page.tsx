"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { AlertCircle, Building2, Mail, Phone } from "lucide-react";
import { apiClient } from "@/lib/api/client";

export default function EmployerSignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<"signup" | "otp">("signup");
  const [otp, setOtp] = useState("");
  const [testOtp, setTestOtp] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    organizationName: "",
    hrFirstName: "",
    hrMiddleName: "",
    hrLastName: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
  });

  const handleSignup = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (formData.password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await apiClient<{ message?: string; testOtp?: string }>(
        "/auth/register/employer",
        {
          method: "POST",
          body: JSON.stringify({
            organization_name: formData.organizationName,
            hr_first_name: formData.hrFirstName,
            hr_middle_name: formData.hrMiddleName,
            hr_last_name: formData.hrLastName,
            email: formData.email,
            phone: formData.phone,
            password: formData.password,
          }),
        }
      );
      setTestOtp(result.testOtp ?? "");
      setStep("otp");
    } catch (signupError: unknown) {
      setError(signupError instanceof Error ? signupError.message : "Signup failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyOTP = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const query = new URLSearchParams({ email: formData.email, code: otp });
      await apiClient(`/auth/verify-email?${query.toString()}`, { method: "POST" });
      router.push(
        `/login?role=employer&verified=1&email=${encodeURIComponent(formData.email)}`
      );
    } catch (verificationError: unknown) {
      setError(
        verificationError instanceof Error
          ? verificationError.message
          : "Email verification failed."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <header className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary-100 text-primary-600">
            <Building2 className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            {step === "signup" ? "Employer Registration" : "Verify Your Organization Email"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {step === "signup"
              ? "Create your organization login. You will build the full profile after email verification."
              : `Enter the six-digit verification code sent to ${formData.email}.`}
          </p>
        </header>

        {error && (
          <p
            role="alert"
            className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </p>
        )}

        {step === "signup" ? (
          <form onSubmit={handleSignup} className="space-y-4">
            <label className="block text-sm font-medium text-slate-700">
              Organization Name *
              <input
                required
                autoComplete="organization"
                value={formData.organizationName}
                onChange={(event) =>
                  setFormData({ ...formData, organizationName: event.target.value })
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>

            <fieldset>
              <legend className="mb-1 text-sm font-medium text-slate-700">
                HR Representative Name *
              </legend>
              <div className="grid grid-cols-3 gap-2">
                <input
                  required
                  autoComplete="given-name"
                  placeholder="First name"
                  value={formData.hrFirstName}
                  onChange={(event) =>
                    setFormData({ ...formData, hrFirstName: event.target.value })
                  }
                  className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
                />
                <input
                  required
                  placeholder="Middle name"
                  value={formData.hrMiddleName}
                  onChange={(event) =>
                    setFormData({ ...formData, hrMiddleName: event.target.value })
                  }
                  className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
                />
                <input
                  required
                  autoComplete="family-name"
                  placeholder="Last name"
                  value={formData.hrLastName}
                  onChange={(event) =>
                    setFormData({ ...formData, hrLastName: event.target.value })
                  }
                  className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
                />
              </div>
            </fieldset>

            <label className="block text-sm font-medium text-slate-700">
              <span className="flex items-center gap-1">
                <Mail className="h-3 w-3 text-slate-400" />
                Organization Email *
              </span>
              <input
                required
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={(event) =>
                  setFormData({ ...formData, email: event.target.value })
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="hr@yourhospital.com"
              />
            </label>

            <label className="block text-sm font-medium text-slate-700">
              <span className="flex items-center gap-1">
                <Phone className="h-3 w-3 text-slate-400" />
                Organization Phone *
              </span>
              <input
                required
                type="tel"
                autoComplete="tel"
                value={formData.phone}
                onChange={(event) =>
                  setFormData({ ...formData, phone: event.target.value })
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="+251 9XX XXX XXX"
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm font-medium text-slate-700">
                Password * <span className="font-normal text-slate-500">(12+ characters)</span>
                <input
                  required
                  minLength={12}
                  type="password"
                  autoComplete="new-password"
                  value={formData.password}
                  onChange={(event) =>
                    setFormData({ ...formData, password: event.target.value })
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Confirm Password *
                <input
                  required
                  minLength={12}
                  type="password"
                  autoComplete="new-password"
                  value={formData.confirmPassword}
                  onChange={(event) =>
                    setFormData({ ...formData, confirmPassword: event.target.value })
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </label>
            </div>

            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Create Account
            </Button>
            <p className="pt-2 text-center text-xs text-slate-400">
              Already registered?{" "}
              <Link href="/login?role=employer" className="text-primary-600">
                Sign in
              </Link>
            </p>
          </form>
        ) : (
          <form onSubmit={handleVerifyOTP} className="space-y-4">
            <label className="block text-sm font-medium text-slate-700">
              Six-Digit Verification Code *
              <input
                required
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                autoComplete="one-time-code"
                value={otp}
                onChange={(event) => setOtp(event.target.value.replace(/\D/g, ""))}
                className="mt-1 w-full rounded-lg border-2 border-slate-300 px-3 py-3 text-center font-mono text-2xl tracking-[0.5em] focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
                placeholder="••••••"
              />
            </label>

            {testOtp && (
              <div className="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <p>
                  <strong className="block text-xs uppercase tracking-wide">
                    Development test code
                  </strong>
                  <span className="font-mono text-lg font-bold tracking-widest">
                    {testOtp}
                  </span>
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setOtp(testOtp)}
                >
                  Use this code
                </Button>
              </div>
            )}

            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Verify Email
            </Button>
            <button
              type="button"
              onClick={() => setStep("signup")}
              className="w-full text-xs text-slate-500 hover:text-slate-700"
            >
              Back to registration
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
