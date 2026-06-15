import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { saveToken } from "../../client_frontend/credentials/oauth_token_store.js";
import { loadApiKey, saveApiKey } from "../../client_frontend/credentials/keystore.js";
import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

function createStateDir(baseDir) {
  return path.join(baseDir, "state");
}

test("config current exposes sanitized credential_state without token leakage", async () => {
  const fixture = createSimpleServerFixture("vp-oauth-http-");
  const stateDir = createStateDir(fixture.appHome);
  await saveToken(stateDir, {
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
  });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const payload = await (await fetch(`${baseUrl}/config/api/current`)).json();
    assert.equal(payload.credential_state.auth_mode, "oauth");
    assert.equal(payload.credential_state.oauth_session.account_label.includes("OpenAI"), true);
    assert.equal(JSON.stringify(payload).includes("oauth-token"), false);
    assert.equal(JSON.stringify(payload).includes("oauth-refresh"), false);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("oauth login redirects to the localhost loopback callback used by the orchestrator flow", async () => {
  const fixture = createSimpleServerFixture("vp-oauth-http-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const loginRes = await fetch(`${baseUrl}/config/oauth/login`, { redirect: "manual" });
    const location = String(loginRes.headers.get("location") || "");
    assert.equal(loginRes.status, 302);
    assert.match(location, /^https:\/\/auth\.openai\.com\/oauth\/authorize\?/);
    assert.match(decodeURIComponent(location), /redirect_uri=http:\/\/localhost:1455\/auth\/callback/);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config test-llm returns 409 while an active OAuth session is present", async () => {
  const fixture = createSimpleServerFixture("vp-oauth-http-", { admin_secret: "admin-pass", llm_api_key: "sk-fallback" });
  const stateDir = createStateDir(fixture.appHome);
  await saveToken(stateDir, {
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
  });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const unlockRes = await fetch(`${baseUrl}/config/api/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret: "admin-pass" })
    });
    const cookie = extractCookie(unlockRes);
    const llmTestRes = await fetch(`${baseUrl}/config/api/test-llm`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ model: "gpt-4.1" })
    });
    const payload = await llmTestRes.json();
    assert.equal(llmTestRes.status, 409);
    assert.match(payload.message, /OAuth session is active/i);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("health derives auth mode and readiness from the credential resolver", async () => {
  const fixture = createSimpleServerFixture("vp-oauth-http-", { llm_api_key: "", embedding_api_key: "sk-embed" });
  const stateDir = createStateDir(fixture.appHome);
  await saveToken(stateDir, {
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
  });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: false });
  const baseUrl = await listen(app.server);

  try {
    const payload = await (await fetch(`${baseUrl}/api/v2/health`)).json();
    assert.equal(payload.llm_auth_mode, "oauth");
    assert.equal(payload.llm_ready, true);
    assert.equal(payload.embedding_ready, true);
    assert.equal(payload.oauth_session.status, "connected");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config delete-api-key removes only the selected provider credential slot", async () => {
  const fixture = createSimpleServerFixture("vp-oauth-http-", {
    llm_provider: "openai",
    llm_base_url: "https://api.openai.com/v1"
  });
  const stateDir = createStateDir(fixture.appHome);
  await saveApiKey(stateDir, "llm_shared", "openai-secret", {
    provider_id: "openai",
    base_url: "https://api.openai.com/v1"
  });
  await saveApiKey(stateDir, "llm_shared", "openrouter-secret", {
    provider_id: "openrouter",
    base_url: "https://openrouter.ai/api/v1"
  });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const deleteRes = await fetch(`${baseUrl}/config/api/delete-api-key`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        group: "llm_shared",
        provider: "openrouter",
        base_url: "https://openrouter.ai/api/v1"
      })
    });
    const payload = await deleteRes.json();
    assert.equal(deleteRes.status, 200);
    assert.equal(payload.deleted, true);
    assert.match(payload.message, /OpenRouter/);
    assert.equal(await loadApiKey(stateDir, "llm_shared", {
      provider_id: "openrouter",
      base_url: "https://openrouter.ai/api/v1"
    }), "");
    assert.equal(await loadApiKey(stateDir, "llm_shared", {
      provider_id: "openai",
      base_url: "https://api.openai.com/v1"
    }), "openai-secret");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
