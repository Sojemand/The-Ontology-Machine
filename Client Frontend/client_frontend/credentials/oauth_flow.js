import { URLSearchParams } from "node:url";

import { buildTokenBundle } from "./oauth_metadata.js";
import { postJson } from "./oauth_http.js";
import { buildCodeChallenge, generateCodeVerifier, generateState } from "./oauth_pkce.js";
import { OAUTH_AUTHORIZE_URL, OAUTH_CLIENT_ID, OAUTH_SCOPE, OAUTH_TOKEN_URL } from "./policy.js";
import { assertPendingLogin } from "./validation.js";

function errorDetail(response) {
  return String(response.body?.error_description || response.body?.error || response.body?.detail || "request failed");
}

export function buildAuthorizationUrl({ clientId = OAUTH_CLIENT_ID, callbackUrl, scope = OAUTH_SCOPE, state, codeVerifier }) {
  const query = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: callbackUrl,
    scope,
    state,
    code_challenge: buildCodeChallenge(codeVerifier),
    code_challenge_method: "S256",
    id_token_add_organizations: "true",
    codex_cli_simplified_flow: "true"
  });
  return `${OAUTH_AUTHORIZE_URL}?${query.toString()}`;
}

export function beginOAuthLogin({ clientId = OAUTH_CLIENT_ID, scope = OAUTH_SCOPE, callbackUrl, pendingLogins }) {
  const state = generateState();
  const codeVerifier = generateCodeVerifier();
  pendingLogins.start({ state, code_verifier: codeVerifier, callback_url: callbackUrl });
  return buildAuthorizationUrl({ clientId, callbackUrl, scope, state, codeVerifier });
}

export async function completeOAuthLogin({
  clientId = OAUTH_CLIENT_ID,
  callbackUrl,
  params,
  pendingLogins
}) {
  const error = String(params.get("error") || "").trim();
  if (error) {
    throw new Error(String(params.get("error_description") || error));
  }
  const code = String(params.get("code") || "").trim();
  const state = String(params.get("state") || "").trim();
  if (!code || !state) {
    throw new Error("OAuth callback does not contain a valid code.");
  }
  const pending = pendingLogins.consume(state);
  assertPendingLogin(pending, callbackUrl);
  const response = await postJson(OAUTH_TOKEN_URL, {
    payload: {
      grant_type: "authorization_code",
      client_id: clientId,
      code,
      code_verifier: pending.code_verifier,
      redirect_uri: callbackUrl
    }
  });
  if (response.status_code >= 400) {
    throw new Error(`OAuth token exchange failed (${response.status_code}): ${errorDetail(response)}`);
  }
  return buildTokenBundle({
    ...response.body,
    status_code: response.status_code,
    fallback_client_id: clientId
  });
}

export async function refreshOAuthToken(token) {
  const response = await postJson(OAUTH_TOKEN_URL, {
    payload: {
      grant_type: "refresh_token",
      client_id: token.client_id,
      refresh_token: token.refresh_token
    }
  });
  if (response.status_code >= 400) {
    throw new Error(`OAuth refresh failed (${response.status_code}): ${errorDetail(response)}`);
  }
  const refreshed = buildTokenBundle({
    ...response.body,
    status_code: response.status_code,
    fallback_client_id: token.client_id,
    fallback_account_id: token.account_id,
    fallback_session_id: token.session_id,
    fallback_expires_at: token.expires_at
  });
  return refreshed.refresh_token ? refreshed : { ...refreshed, refresh_token: token.refresh_token };
}
