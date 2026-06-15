import { DEFAULT_OAUTH_SESSION } from "./types.js";
import { providerDefinition, providerOAuthSupported } from "../shared/provider_catalog.js";

export const OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann";
export const OAUTH_SCOPE = "openid profile email offline_access";
export const OAUTH_CALLBACK_PORT = 1455;
export const OAUTH_AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize";
export const OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token";
export const OAUTH_BACKEND_BASE_URL = "https://chatgpt.com/backend-api/codex";
export const OAUTH_BACKEND_RESPONSES_URL = `${OAUTH_BACKEND_BASE_URL}/responses`;

export function providerSettingsForTarget(runtimeConfig = {}, target = "llm_shared") {
  const prefix = target === "embeddings" ? "embedding" : "llm";
  const provider_id = runtimeConfig[`${prefix}_provider`] || "openai";
  const definition = providerDefinition(provider_id);
  const base_url = String(runtimeConfig[`${prefix}_base_url`] || definition.default_base_url || "").trim().replace(/\/+$/, "");
  return {
    provider_id: definition.provider_id,
    display_name: definition.display_name,
    family: definition.family,
    base_url,
    api_key_optional: Boolean(definition.api_key_optional),
    oauth_supported: providerOAuthSupported(definition.provider_id)
  };
}

export function providerLabel(providerSettings = {}) {
  const label = providerSettings.display_name || providerDefinition(providerSettings.provider_id).display_name || "Provider";
  return providerSettings.base_url ? `${label} (${providerSettings.base_url})` : label;
}

export function clientIdHint(clientId) {
  const value = String(clientId || "").trim();
  if (value.length <= 8) {
    return value;
  }
  return `${value.slice(0, 4)}...${value.slice(-4)}`;
}

function accountLabel(accountId) {
  const value = String(accountId || "").trim();
  if (!value) {
    return "OpenAI OAuth";
  }
  if (value.length <= 12) {
    return `OpenAI Account ${value}`;
  }
  return `OpenAI Account ${value.slice(0, 8)}...${value.slice(-4)}`;
}

export function buildLoggedOutSession() {
  return {
    ...DEFAULT_OAUTH_SESSION,
    status: "logged_out",
    status_message: "No active OAuth login. The LLM path uses the configured provider access."
  };
}

export function buildConnectedSession(token, statusMessage = "") {
  return {
    ...DEFAULT_OAUTH_SESSION,
    status: "connected",
    account_label: accountLabel(token?.account_id),
    status_message:
      statusMessage || "OAuth is active. The LLM path primarily uses OAuth; the API key remains a fallback.",
    client_id_hint: clientIdHint(token?.client_id),
    scope: String(token?.scope || "").trim(),
    expires_at: String(token?.expires_at || "").trim(),
    account_id: String(token?.account_id || "").trim(),
    has_refresh_token: Boolean(token?.refresh_token)
  };
}

export function buildErrorSession(message, previous = DEFAULT_OAUTH_SESSION) {
  return {
    ...DEFAULT_OAUTH_SESSION,
    ...previous,
    status: "error",
    status_message: String(message || "The saved OAuth session is not ready to use.").trim()
  };
}
