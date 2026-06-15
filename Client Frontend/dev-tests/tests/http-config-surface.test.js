import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";
import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

function policyPath(fixture) {
  return path.join(fixture.configDir, "frontend_policy.json");
}

test("config current returns frontend_policy defaults plus diagnostics for invalid stored policy", async () => {
  const fixture = createSimpleServerFixture("vp-config-http-");
  writeFileSync(policyPath(fixture), "{ broken", "utf8");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const payload = await (await fetch(`${baseUrl}/config/api/current`)).json();
    assert.equal(payload.frontend_policy.chat_history.max_history, 100);
    assert.equal(payload.frontend_policy_diagnostics.status, "invalid_json");
    assert.equal(payload.frontend_policy_diagnostics.raw_text, "{ broken");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config page is served without browser cache so UI bundles cannot go stale", async () => {
  const fixture = createSimpleServerFixture("vp-config-static-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const response = await fetch(`${baseUrl}/config`);

    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store, max-age=0");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config current returns policy_path for invalid stored frontend_policy content", async () => {
  const fixture = createSimpleServerFixture("vp-config-http-");
  const invalidPolicy = buildDefaultFrontendPolicy();
  invalidPolicy.chat_history = {};
  writeFileSync(policyPath(fixture), JSON.stringify(invalidPolicy), "utf8");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const payload = await (await fetch(`${baseUrl}/config/api/current`)).json();
    assert.equal(payload.frontend_policy_diagnostics.status, "invalid_policy");
    assert.equal(payload.frontend_policy_diagnostics.policy_path, "frontend_policy.chat_history");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config save persists config.json and frontend_policy.json together", async () => {
  const fixture = createSimpleServerFixture("vp-config-http-", { admin_secret: "admin-pass" });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const customDbPath = path.join(fixture.corpusRoot, "custom-corpus.db");
    writeFileSync(customDbPath, readFileSync(fixture.dbPath));
    const customDb = new DatabaseSync(customDbPath);
    customDb.prepare(`
      INSERT INTO documents (
        id, file_name, file_path, content_hash, document_type, page_count, content_free_text
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run("doc-2", "beta.pdf", "data/beta.pdf", "sha256:bbbb", "invoice", 1, "Hello again");
    customDb.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .run("doc-2", "title", "Title", "string", "title", "Second Doc", 0, 1);
    customDb.close();

    const unlockRes = await fetch(`${baseUrl}/config/api/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret: "admin-pass" })
    });
    const cookie = extractCookie(unlockRes);
    const frontendPolicy = buildDefaultFrontendPolicy();
    frontendPolicy.chat_history.max_history = 5;
    const saveRes = await fetch(`${baseUrl}/config/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ customer_name: "Saved Customer", sql_database_path: customDbPath, frontend_policy: frontendPolicy })
    });
    const payload = await saveRes.json();
    assert.equal(saveRes.status, 200);
    assert.equal(payload.config.customer_name, "Saved Customer");
    assert.equal(payload.config.sql_database_path, customDbPath);
    assert.equal(payload.config.frontend_policy.chat_history.max_history, 5);
    assert.equal(JSON.parse(readFileSync(path.join(fixture.configDir, "config.json"), "utf8")).customer_name, "Saved Customer");
    assert.equal(JSON.parse(readFileSync(path.join(fixture.configDir, "config.json"), "utf8")).sql_database_path, customDbPath);
    assert.equal(JSON.parse(readFileSync(policyPath(fixture), "utf8")).chat_history.max_history, 5);

    const healthPayload = await (await fetch(`${baseUrl}/api/v2/health`)).json();
    assert.equal(healthPayload.corpus_docs, 2);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config save rejects an unreadable sql_database_path with a field marker", async () => {
  const fixture = createSimpleServerFixture("vp-config-http-", { admin_secret: "admin-pass" });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const unlockRes = await fetch(`${baseUrl}/config/api/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret: "admin-pass" })
    });
    const cookie = extractCookie(unlockRes);
    const saveRes = await fetch(`${baseUrl}/config/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ sql_database_path: path.join(fixture.corpusRoot, "missing-corpus.db"), frontend_policy: buildDefaultFrontendPolicy() })
    });
    const payload = await saveRes.json();
    assert.equal(saveRes.status, 400);
    assert.equal(payload.field, "sql_database_path");
    assert.match(payload.error, /SQL database/i);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config save rejects invalid frontend_policy with a precise field marker", async () => {
  const fixture = createSimpleServerFixture("vp-config-http-", { admin_secret: "admin-pass" });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const unlockRes = await fetch(`${baseUrl}/config/api/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret: "admin-pass" })
    });
    const cookie = extractCookie(unlockRes);
    const invalidPolicy = buildDefaultFrontendPolicy();
    invalidPolicy.chat_history = {};
    const saveRes = await fetch(`${baseUrl}/config/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ frontend_policy: invalidPolicy })
    });
    const payload = await saveRes.json();
    assert.equal(saveRes.status, 400);
    assert.equal(payload.field, "frontend_policy");
    assert.match(payload.error, /chat_history/i);
    assert.equal(payload.policy_path, "frontend_policy.chat_history");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("config save stays fail-closed while protected and not unlocked", async () => {
  const fixture = createSimpleServerFixture("vp-config-http-", { admin_secret: "admin-pass" });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, configMode: true });
  const baseUrl = await listen(app.server);

  try {
    const saveRes = await fetch(`${baseUrl}/config/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frontend_policy: buildDefaultFrontendPolicy() })
    });
    const payload = await saveRes.json();
    assert.equal(saveRes.status, 403);
    assert.match(payload.error, /unlock required/i);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
