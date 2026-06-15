import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { normalizeStoredSqlDatabasePath, resolveSqlDatabasePath } from "../../client_frontend/config/database_path.js";
import { DEFAULT_CONFIG, DEFAULT_SQL_DATABASE_PATH } from "../../server/config.js";
import { createApplication } from "../../server/index.js";
import { cleanupFixture, createServerFixture, listen, writeFrontendConfig, writeFrontendShell } from "./server-fixtures.js";

test("default config points at the bundled sample corpus outside the frontend module", () => {
  const moduleRoot = "C:\\Ontology Machine\\Client Frontend";
  assert.equal(DEFAULT_CONFIG.sql_database_path, DEFAULT_SQL_DATABASE_PATH);
  assert.equal(normalizeStoredSqlDatabasePath("   "), "");
  assert.equal(
    resolveSqlDatabasePath(moduleRoot, DEFAULT_CONFIG),
    path.resolve(moduleRoot, DEFAULT_SQL_DATABASE_PATH)
  );
});

test("explicitly unconfigured corpus still fails closed", () => {
  assert.throws(
    () => resolveSqlDatabasePath("C:\\Module", { ...DEFAULT_CONFIG, sql_database_path: "" }),
    /SQL database path is not configured/
  );
});

test("application starts without a configured corpus and chat fails closed", async () => {
  const fixture = createServerFixture("vp-corpus-governance-");
  let agentBuilt = false;
  writeFrontendShell(fixture);
  writeFrontendConfig(fixture, { sql_database_path: "" });
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => {
      agentBuilt = true;
      throw new Error("agent should not be built without an active corpus");
    }
  });
  const baseUrl = await listen(app.server);

  try {
    const health = await (await fetch(`${baseUrl}/api/v2/health`)).json();
    assert.equal(agentBuilt, false);
    assert.equal(health.corpus_docs, 0);

    const chatRes = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Hallo" })
    });
    const payload = await chatRes.json();
    assert.equal(chatRes.status, 409);
    assert.equal(payload.field, "sql_database_path");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
