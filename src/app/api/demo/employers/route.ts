import { NextRequest, NextResponse } from "next/server";
import {
  registerDemoEmployer,
  type EmployerRegistrationInput,
} from "@/lib/demo/invitations";
import { isLocalDemoRequest } from "@/lib/demo/request-guards";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  if (!isLocalDemoRequest(request)) {
    return NextResponse.json({ error: "Demo registration is unavailable." }, { status: 404 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid employer registration." }, { status: 400 });
  }
  if (typeof body !== "object" || body === null) {
    return NextResponse.json({ error: "Complete all employer registration fields." }, { status: 400 });
  }

  const keys: (keyof EmployerRegistrationInput)[] = [
    "organizationName",
    "hrFirstName",
    "hrMiddleName",
    "hrLastName",
    "email",
    "phone",
    "password",
  ];
  const input = {} as EmployerRegistrationInput;
  for (const key of keys) {
    const value = (body as Record<string, unknown>)[key];
    if (typeof value !== "string" || value.length > 2_800_000) {
      return NextResponse.json({ error: "Complete all employer registration fields." }, { status: 400 });
    }
    input[key] = value;
  }

  const result = registerDemoEmployer(input);
  const { testOtp, ...response } = result;
  return NextResponse.json(
    {
      ...response,
      ...(result.success && process.env.NODE_ENV !== "production" ? { testOtp } : {}),
    },
    { status: result.success ? 201 : 400 }
  );
}
