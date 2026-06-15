import { OAUTH_BACKEND_RESPONSES_URL } from "../credentials/policy.js";
import { PROVIDER_REQUEST_TIMEOUT_MS } from "./adapter_core.js";
import { buildBackendPayload } from "./oauth_payload.js";
import { buildAssistantMessage, decodeSseEvents } from "./oauth_stream.js";

const DEFAULT_ORIGINATOR = "codex_cli_rs";
const DEFAULT_USER_AGENT = "codex-cli/0.108.0-alpha.12";

function redactSecrets(text) {
  return String(text || "")
    .replace(/"access_token"\s*:\s*"[^"]+"/gi, '"access_token":"[REDACTED]"')
    .replace(/"refresh_token"\s*:\s*"[^"]+"/gi, '"refresh_token":"[REDACTED]"')
    .replace(/Bearer\s+[A-Za-z0-9._-]+/g, "Bearer [REDACTED]")
    .replace(/OPENAI_API_KEY=[^\s"']+/g, "OPENAI_API_KEY=[REDACTED]");
}

export async function requestOAuthChatCompletion(runtimeAuth, messages, options = {}) {
  const response = await fetch(OAUTH_BACKEND_RESPONSES_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${runtimeAuth.access_token}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      originator: DEFAULT_ORIGINATOR,
      "User-Agent": DEFAULT_USER_AGENT,
      ...(runtimeAuth.account_id ? { "ChatGPT-Account-Id": runtimeAuth.account_id } : {})
    },
    body: JSON.stringify(buildBackendPayload(messages, options)),
    signal: AbortSignal.timeout(PROVIDER_REQUEST_TIMEOUT_MS)
  });
  const rawText = await response.text();
  if (!response.ok) {
    throw new Error(`OAuth backend error ${response.status}: ${redactSecrets(rawText) || response.statusText}`);
  }
  const events = decodeSseEvents(rawText);
  const errorEvent = events.find((event) => event.event === "error");
  if (errorEvent) {
    throw new Error(`OAuth backend error: ${redactSecrets(errorEvent.data?.message || errorEvent.data?.error || "stream error")}`);
  }
  return { choices: [{ message: buildAssistantMessage(events) }] };
}
