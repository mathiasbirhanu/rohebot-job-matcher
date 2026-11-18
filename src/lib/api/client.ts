// src/lib/api/client.ts

// In production, if no API URL is set, we use a relative path so it hits
// the same Vercel domain (which avoids localhost issues).
// In local dev, we default to localhost:8000 (your expected backend).
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8000/api");

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function apiUrl(endpoint: string): string {
  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL.replace(/\/+$/, "")}${normalizedEndpoint}`;
}

function getErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === "string" && data) return data;
  if (data && typeof data === "object") {
    const body = data as Record<string, unknown>;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      const messages = body.detail.flatMap((item) => {
        if (!item || typeof item !== "object") return [];
        const validation = item as Record<string, unknown>;
        if (typeof validation.msg !== "string") return [];
        const location = Array.isArray(validation.loc)
          ? validation.loc.filter((part): part is string | number => typeof part === "string" || typeof part === "number").join(".")
          : "";
        return [location ? `${location}: ${validation.msg}` : validation.msg];
      });
      if (messages.length) return messages.join("; ");
    }
    if (typeof body.error === "string") return body.error;
    if (typeof body.message === "string") return body.message;
  }
  return fallback;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = apiUrl(endpoint);

  const headers = new Headers(options.headers);
  if (typeof FormData !== "undefined" && options.body instanceof FormData) {
    headers.delete("Content-Type");
  } else if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    credentials: options.credentials ?? "include",
    headers,
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new ApiError(
      response.status,
      getErrorMessage(errorData, response.statusText || "The API request failed."),
      errorData
    );
  }

  // Handle 204 No Content
  if (response.status === 204) return {} as T;

  return response.json();
}