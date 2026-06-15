type FetchLike = typeof fetch;

export class ApiError extends Error {
  status: number;
  payload: Record<string, unknown> | null;

  constructor(message: string, status: number, payload: Record<string, unknown> | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function mergeHeaders(init?: RequestInit): HeadersInit {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return headers;
}

export function extractErrorMessage(response: Response, rawText: string): string {
  const trimmed = rawText.trim();
  if (!trimmed) {
    return `HTTP ${response.status}`;
  }

  try {
    const payload = JSON.parse(trimmed);
    if (typeof payload?.error === "string") {
      return payload.error;
    }
    if (typeof payload?.message === "string") {
      return payload.message;
    }
  } catch {
    // Fall back to the raw response text.
  }

  return trimmed;
}

function extractErrorPayload(rawText: string): Record<string, unknown> | null {
  try {
    const payload = JSON.parse(rawText.trim());
    return payload && typeof payload === "object" && !Array.isArray(payload) ? payload as Record<string, unknown> : null;
  } catch {
    return null;
  }
}

export async function requestWithFetch<T>(
  fetchImpl: FetchLike,
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  const response = await fetchImpl(input, {
    credentials: "same-origin",
    ...init,
    headers: mergeHeaders(init)
  });

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const rawText = await response.text();
    throw new ApiError(extractErrorMessage(response, rawText), response.status, extractErrorPayload(rawText));
  }

  return (await response.json()) as T;
}

export type { FetchLike };
