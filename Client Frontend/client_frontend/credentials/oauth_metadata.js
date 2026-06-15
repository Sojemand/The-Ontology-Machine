function decodeJwtClaims(token) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) {
    return {};
  }
  try {
    return JSON.parse(Buffer.from(`${parts[1]}${"=".repeat((4 - (parts[1].length % 4)) % 4)}`, "base64url").toString("utf8"));
  } catch {
    return {};
  }
}

function normalizeTokenType(tokenType) {
  const value = String(tokenType || "Bearer").trim();
  return value.toLowerCase() === "bearer" ? "Bearer" : value;
}

function isoFromUnix(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Date(numeric * 1000).toISOString() : "";
}

export function buildTokenBundle({
  access_token = "",
  refresh_token = "",
  id_token = "",
  token_type = "Bearer",
  scope = "",
  account_id = "",
  expires_at = "",
  client_id = "",
  session_id = "",
  status_code = 200,
  token_status_code = 200,
  fallback_account_id = "",
  fallback_expires_at = "",
  fallback_client_id = "",
  fallback_session_id = ""
} = {}) {
  const accessClaims = decodeJwtClaims(access_token);
  const idClaims = decodeJwtClaims(id_token);
  const authClaims = accessClaims["https://api.openai.com/auth"] || idClaims["https://api.openai.com/auth"] || {};
  return {
    access_token: String(access_token || ""),
    refresh_token: String(refresh_token || ""),
    id_token: String(id_token || ""),
    token_type: normalizeTokenType(token_type),
    expires_at: String(expires_at || fallback_expires_at || isoFromUnix(accessClaims.exp)),
    account_id: String(authClaims.chatgpt_account_id || account_id || fallback_account_id || ""),
    client_id: String(accessClaims.client_id || client_id || fallback_client_id || ""),
    session_id: String(accessClaims.session_id || idClaims.sid || session_id || fallback_session_id || ""),
    scope: String(scope || accessClaims.scp || ""),
    token_status_code: Number(token_status_code || status_code) || 200
  };
}
