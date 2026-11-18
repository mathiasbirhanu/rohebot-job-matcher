import { NextRequest, NextResponse } from "next/server";
import {
  getDemoEmployerProfile,
  saveDemoEmployerProfile,
  type EmployerProfileInput,
} from "@/lib/demo/invitations";
import { isLocalDemoRequest } from "@/lib/demo/request-guards";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  if (!isLocalDemoRequest(request)) {
    return NextResponse.json({ error: "Employer profile setup is unavailable." }, { status: 404 });
  }
  const sessionId = request.cookies.get("rohobot_session")?.value;
  if (!sessionId || request.cookies.get("rohobot_role")?.value !== "employer") {
    return NextResponse.json({ error: "Sign in with your employer account to build your profile." }, { status: 401 });
  }
  const profile = getDemoEmployerProfile(sessionId);
  if (!profile) {
    return NextResponse.json({ error: "Your employer session has expired. Please sign in again." }, { status: 401 });
  }
  return NextResponse.json({ profile });
}

export async function POST(request: NextRequest) {
  if (!isLocalDemoRequest(request)) {
    return NextResponse.json({ error: "Employer profile setup is unavailable." }, { status: 404 });
  }
  const sessionId = request.cookies.get("rohobot_session")?.value;
  if (!sessionId || request.cookies.get("rohobot_role")?.value !== "employer") {
    return NextResponse.json({ error: "Sign in with your employer account to build your profile." }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid organization profile." }, { status: 400 });
  }
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return NextResponse.json({ error: "Complete the required organization profile fields." }, { status: 400 });
  }
  const keys: (keyof EmployerProfileInput)[] = [
    "organizationName",
    "organizationType",
    "tinNumber",
    "website",
    "hrEmail",
    "hrPhone",
    "address",
    "logoFileName",
    "businessLicenseFileName",
    "businessLicenseDataUrl",
  ];
  const profile = {} as EmployerProfileInput;
  for (const key of keys) {
    const value = (body as Record<string, unknown>)[key];
    if (typeof value !== "string" || value.length > 2_800_000) {
      return NextResponse.json({ error: "Complete the required organization profile fields." }, { status: 400 });
    }
    profile[key] = value;
  }

  const result = saveDemoEmployerProfile(sessionId, profile);
  return NextResponse.json(result, { status: result.success ? 200 : 400 });
}
