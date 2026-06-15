import assert from "node:assert/strict";
import { linkSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { loadApiKey, saveApiKey } from "../../client_frontend/credentials/keystore.js";
import { loadToken, saveToken } from "../../client_frontend/credentials/oauth_token_store.js";
import { writeOAuthReport } from "../../client_frontend/credentials/oauth_report.js";
import { loadCredentialsState, saveCredentialsState } from "../../client_frontend/credentials/repository.js";
import { loadStoredModelCatalogState, saveModelCatalogState } from "../../client_frontend/model_catalog/repository.js";
import { cleanupTempDir, makeTempDir } from "./config-test-fixtures.js";

const PROVIDER_SETTINGS = {
  provider_id: "openai",
  base_url: "https://api.openai.com/v1"
};

function linkOrSkip(t, sourcePath, targetPath) {
  try {
    linkSync(sourcePath, targetPath);
    return true;
  } catch (error) {
    t.skip(`hard links unavailable for atomic replacement probe: ${error instanceof Error ? error.message : String(error)}`);
    return false;
  }
}

test("credential keystore replaces store without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const storePath = path.join(tempDir, "keystore.enc");
    const linkedPath = path.join(tempDir, "linked-keystore.enc");
    await saveApiKey(tempDir, "llm", "sk-before", PROVIDER_SETTINGS);
    if (!linkOrSkip(t, storePath, linkedPath)) return;

    await saveApiKey(tempDir, "llm", "sk-after", PROVIDER_SETTINGS);

    assert.equal(await loadApiKey(tempDir, "llm", PROVIDER_SETTINGS), "sk-after");
    assert.notEqual(readFileSync(storePath, "utf8"), readFileSync(linkedPath, "utf8"));
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("credential keystore mutations fail closed on corrupt existing store", async () => {
  const tempDir = makeTempDir();
  try {
    const storePath = path.join(tempDir, "keystore.enc");
    writeFileSync(storePath, "{broken", "utf8");

    await assert.rejects(
      saveApiKey(tempDir, "llm", "sk-new", PROVIDER_SETTINGS),
      /Credential keystore could not be read/
    );

    assert.equal(readFileSync(storePath, "utf8"), "{broken");
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("credential keystore reads fail closed on corrupt existing store", async () => {
  const tempDir = makeTempDir();
  try {
    const storePath = path.join(tempDir, "keystore.enc");
    writeFileSync(storePath, "{broken", "utf8");

    await assert.rejects(
      loadApiKey(tempDir, "llm", PROVIDER_SETTINGS),
      /Credential keystore could not be read/
    );
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("OAuth token cache replaces token without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const tokenPath = path.join(tempDir, "oauth_token.enc");
    const linkedPath = path.join(tempDir, "linked-oauth-token.enc");
    await saveToken(tempDir, {
      access_token: "token-before",
      refresh_token: "refresh-before",
      id_token: "",
      token_type: "Bearer",
      expires_at: "2099-01-01T00:00:00.000Z",
      account_id: "account-1",
      client_id: "client-1",
      session_id: "session-1",
      scope: "openid profile",
      token_status_code: 200
    });
    if (!linkOrSkip(t, tokenPath, linkedPath)) return;

    await saveToken(tempDir, {
      access_token: "token-after",
      refresh_token: "refresh-after",
      id_token: "",
      token_type: "Bearer",
      expires_at: "2099-01-01T00:00:00.000Z",
      account_id: "account-1",
      client_id: "client-1",
      session_id: "session-2",
      scope: "openid profile",
      token_status_code: 200
    });

    assert.equal((await loadToken(tempDir)).access_token, "token-after");
    assert.notEqual(readFileSync(tokenPath, "utf8"), readFileSync(linkedPath, "utf8"));
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("OAuth token cache reads fail closed on corrupt existing token", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "oauth_token.enc"), "{broken", "utf8");

    await assert.rejects(
      loadToken(tempDir),
      /OAuth token cache could not be read/
    );
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("credentials state replaces session state without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const statePath = path.join(tempDir, "credentials_state.json");
    const linkedPath = path.join(tempDir, "linked-credentials-state.json");
    await saveCredentialsState(tempDir, {
      targets: { llm_shared: { has_secret: true }, embeddings: { has_secret: false } },
      oauth_session: { status: "connected", account_label: "Before" }
    });
    if (!linkOrSkip(t, statePath, linkedPath)) return;

    await saveCredentialsState(tempDir, {
      targets: { llm_shared: { has_secret: false }, embeddings: { has_secret: true } },
      oauth_session: { status: "connected", account_label: "After" }
    });

    assert.equal((await loadCredentialsState(tempDir)).oauth_session.account_label, "After");
    assert.equal(JSON.parse(readFileSync(linkedPath, "utf8")).oauth_session.account_label, "Before");
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("credentials state reads fail closed on corrupt existing state", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "credentials_state.json"), "{broken", "utf8");

    await assert.rejects(
      loadCredentialsState(tempDir),
      /Credentials state could not be read/
    );
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("OAuth report replaces support report without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const reportPath = path.join(tempDir, "oauth_latest_report.json");
    const linkedPath = path.join(tempDir, "linked-oauth-report.json");
    await writeOAuthReport(tempDir, { event: "before", oauth: { access_token: "token-before" } });
    if (!linkOrSkip(t, reportPath, linkedPath)) return;

    await writeOAuthReport(tempDir, { event: "after", oauth: { refresh_token: "token-after", visible: "ok" } });

    const report = JSON.parse(readFileSync(reportPath, "utf8"));
    const linkedReport = JSON.parse(readFileSync(linkedPath, "utf8"));
    assert.equal(report.event, "after");
    assert.equal(report.oauth.refresh_token, "[REDACTED]");
    assert.equal(linkedReport.event, "before");
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("model catalog state replaces cache without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const catalogPath = path.join(tempDir, "model_catalog_state.json");
    const linkedPath = path.join(tempDir, "linked-model-catalog-state.json");
    await saveModelCatalogState(tempDir, {
      llm_shared: { models: ["model-before"], source: "live", refreshed_at: "before", provider_id: "openai", base_url: "https://api.openai.com/v1" },
      embeddings: { models: [], source: "seed", refreshed_at: "", provider_id: "", base_url: "" },
      llm_shared_catalogs: [],
      embeddings_catalogs: []
    });
    if (!linkOrSkip(t, catalogPath, linkedPath)) return;

    await saveModelCatalogState(tempDir, {
      llm_shared: { models: ["model-after"], source: "live", refreshed_at: "after", provider_id: "openai", base_url: "https://api.openai.com/v1" },
      embeddings: { models: [], source: "seed", refreshed_at: "", provider_id: "", base_url: "" },
      llm_shared_catalogs: [],
      embeddings_catalogs: []
    });

    assert.deepEqual((await loadStoredModelCatalogState(tempDir)).llm_shared.models, ["model-after"]);
    assert.deepEqual(JSON.parse(readFileSync(linkedPath, "utf8")).llm_shared.models, ["model-before"]);
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});
