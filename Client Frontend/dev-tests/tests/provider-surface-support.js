import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";

export function mockFetch(handler) {
  const original = globalThis.fetch;
  globalThis.fetch = handler;
  return () => {
    globalThis.fetch = original;
  };
}

export function jsonResponse(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

export function createStateDir(prefix = "vp-oauth-provider-") {
  return mkdtempSync(path.join(os.tmpdir(), prefix));
}

export function healthyToken() {
  return {
    access_token: "oauth-token",
    refresh_token: "oauth-refresh",
    id_token: "",
    token_type: "Bearer",
    expires_at: "2099-01-01T00:00:00.000Z",
    account_id: "account-1",
    client_id: "client-1",
    session_id: "session-1",
    scope: "openid profile",
    token_status_code: 200
  };
}
