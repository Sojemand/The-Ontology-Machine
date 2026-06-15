import { DEFAULT_CREDENTIALS_STATE, DEFAULT_OAUTH_SESSION, TARGET_ORDER } from "./types.js";

function coerceBool(value) {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
  }
  return Boolean(value);
}

function coerceText(value) {
  return value == null ? "" : String(value).trim();
}

export function normalizeOAuthSession(value) {
  const payload = value && typeof value === "object" ? value : {};
  const status = coerceText(payload.status);
  return {
    ...DEFAULT_OAUTH_SESSION,
    status: status === "connected" || status === "error" ? status : "logged_out",
    account_label: coerceText(payload.account_label),
    status_message: coerceText(payload.status_message),
    client_id_hint: coerceText(payload.client_id_hint),
    scope: coerceText(payload.scope),
    expires_at: coerceText(payload.expires_at),
    account_id: coerceText(payload.account_id),
    has_refresh_token: coerceBool(payload.has_refresh_token)
  };
}

export function normalizeCredentialsState(value) {
  const payload = value && typeof value === "object" ? value : {};
  const targets = payload.targets && typeof payload.targets === "object" ? payload.targets : {};
  return {
    targets: Object.fromEntries(
      TARGET_ORDER.map((target) => [target, { has_secret: coerceBool(targets?.[target]?.has_secret) }])
    ),
    oauth_session: normalizeOAuthSession(payload.oauth_session)
  };
}

export function expiresWithin(expiresAt, seconds) {
  const parsed = Date.parse(String(expiresAt || ""));
  if (!Number.isFinite(parsed)) {
    return false;
  }
  return parsed <= Date.now() + Math.max(0, Number(seconds) || 0) * 1000;
}

export function isHealthyOAuthSession(session) {
  return normalizeOAuthSession(session).status === "connected";
}

export function assertPendingLogin(pending, callbackUrl) {
  if (!pending) {
    throw new Error("No matching OAuth login attempt found.");
  }
  if (String(pending.callback_url || "") !== String(callbackUrl || "")) {
    throw new Error("OAuth callback does not match the started session.");
  }
}

export function defaultCredentialsState() {
  return normalizeCredentialsState(DEFAULT_CREDENTIALS_STATE);
}
