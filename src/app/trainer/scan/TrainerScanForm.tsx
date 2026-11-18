import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { trainingService } from "@/lib/api/services/training";
import { CheckCircle2, QrCode, UserRound } from "lucide-react";

export function TrainerScanForm() {
  const [isLoading, setIsLoading] = useState(true);
  const [isRegistrationOpen, setIsRegistrationOpen] = useState(false);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [verificationLink, setVerificationLink] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const checkAvailability = () => {
    setIsLoading(true);
    setErrorMessage("");
    trainingService.getQrSettings()
      .then((settings) => {
        setIsRegistrationOpen(settings.active);
        setExpiresAt(settings.expiresAt);
      })
      .catch((error: unknown) => {
        setIsRegistrationOpen(false);
        setErrorMessage(error instanceof Error ? error.message : "Could not check registration availability.");
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    let active = true;
    trainingService.getQrSettings()
      .then((settings) => {
        if (!active) return;
        setIsRegistrationOpen(settings.active);
        setExpiresAt(settings.expiresAt);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setIsRegistrationOpen(false);
        setErrorMessage(error instanceof Error ? error.message : "Could not check registration availability.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const result = await trainingService.registerTrainerFromQR({ firstName, middleName, lastName, email });
      setSuccessMessage(result.message);
      setVerificationLink(result.verificationLink ?? "");
      setFirstName("");
      setMiddleName("");
      setLastName("");
      setEmail("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not register. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-50 text-primary-700">
          {isRegistrationOpen ? <UserRound className="h-7 w-7" /> : <QrCode className="h-7 w-7" />}
        </div>
        <h1 className="text-center text-2xl font-bold text-slate-900">Trainer registration</h1>
        {isLoading ? (
          <p role="status" className="mt-4 text-center text-sm text-slate-500">Checking registration availability...</p>
        ) : isRegistrationOpen ? (
          <>
            <p className="mt-2 text-center text-sm text-slate-600">Enter your name and email address to register for training.</p>
            {expiresAt && <p className="mt-1 text-center text-xs text-slate-500">Registration closes {new Date(expiresAt).toLocaleString()}.</p>}
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <label className="block text-sm font-medium text-slate-700">
                First name
                <input
                  required
                  maxLength={60}
                  autoComplete="given-name"
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Middle name
                <input
                  required
                  maxLength={60}
                  autoComplete="additional-name"
                  value={middleName}
                  onChange={(event) => setMiddleName(event.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Last name
                <input
                  required
                  maxLength={60}
                  autoComplete="family-name"
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Email address
                <input
                  required
                  type="email"
                  maxLength={254}
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5"
                />
              </label>
              {errorMessage && <p role="alert" className="text-sm text-red-700">{errorMessage}</p>}
              {successMessage && (
                <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                  <p className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{successMessage}</span>
                  </p>
                  {verificationLink && (
                    <Link href={verificationLink} className="mt-3 inline-flex font-semibold underline">
                      Verify this email
                    </Link>
                  )}
                  <p className="mt-2 text-xs">
                    This local demo does not deliver email. Open the simulated email inbox to access the verification link.
                  </p>
                </div>
              )}
              <Button type="submit" className="w-full" isLoading={isSubmitting} disabled={isSubmitting}>Register</Button>
            </form>
          </>
        ) : (
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-600">
            {errorMessage || "Trainer registration is currently closed. Please ask the training administrator when registration will reopen."}
          </div>
        )}
        {errorMessage && !isRegistrationOpen && !isLoading && (
          <Button type="button" variant="outline" className="mt-3 w-full" onClick={checkAvailability}>
            Try again
          </Button>
        )}
        <p className="mt-6 text-center text-xs text-slate-500">
          Local demo only. Email delivery is simulated; do not enter sensitive personal information.
        </p>
        <Link href="/" className="mt-4 block text-center text-sm text-primary-700 hover:underline">Back to Rohobot</Link>
      </div>
    </main>
  );
}
