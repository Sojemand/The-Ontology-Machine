import { ContextLengthError } from "./types.js";

export const PROVIDER_REQUEST_TIMEOUT_MS = 300_000;

export function trimBaseUrl(baseUrl) {
  return String(baseUrl || "").replace(/\/+$/, "");
}

export function buildJsonHeaders(apiKey, extra = {}) {
  const headers = { "Content-Type": "application/json", ...extra };
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
  return headers;
}

export function buildOperationMessage(operation, message) {
  return `[provider:${operation}] ${message}`;
}

export async function requestJson(operation, url, init) {
  const response = await fetch(url, { ...init, signal: AbortSignal.timeout(PROVIDER_REQUEST_TIMEOUT_MS) });
  const text = await response.text();
  const payload = parseJsonResponse(operation, response.status, text);
  if (!response.ok) throwProviderError(operation, response, payload);
  return payload;
}

export function messageText(message) {
  const content = typeof message?.content === "string" ? message.content : JSON.stringify(message?.content || "");
  const toolCalls = Array.isArray(message?.tool_calls) && message.tool_calls.length ? `\n[tool_calls]\n${JSON.stringify(message.tool_calls)}` : "";
  return message?.role === "tool" ? `[tool_result ${message.tool_call_id || ""}]\n${content}` : `${content}${toolCalls}`.trim();
}

function parseJsonResponse(operation, status, text) {
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    throw new Error(buildOperationMessage(operation, `LLM provider returned no JSON (HTTP ${status}): ${text.slice(0, 120)}`));
  }
}

function throwProviderError(operation, response, payload) {
  const detail = payload?.error?.message || payload?.error || payload?.message || response.statusText;
  if (/context.length.exceeded|maximum context length/i.test(detail)) {
    throw new ContextLengthError(buildOperationMessage(operation, detail));
  }
  throw new Error(buildOperationMessage(operation, detail || `HTTP ${response.status}`));
}
