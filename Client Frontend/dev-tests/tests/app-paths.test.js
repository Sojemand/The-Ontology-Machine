import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { ensureAppHomeLayout, importStateSnapshot, migrateLegacyRootState, resolveAppPaths } from "../../server/app_paths.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";
import { createApplication } from "../../server/index.js";
import { createStubAgent } from "./http-server-fixtures.js";
import { cleanupFixture, createServerFixture, listen, writeFrontendShell } from "./server-fixtures.js";

function createLegacyChatStore(rootDir) {
  const db = new DatabaseSync(path.join(rootDir, "chats.db"));
  db.exec(`
    CREATE TABLE IF NOT EXISTS chats (
      id TEXT PRIMARY KEY,
      owner_id TEXT NOT NULL DEFAULT '',
      title TEXT NOT NULL DEFAULT '',
      messages TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    )
  `);
  db.prepare(`
    INSERT INTO chats (id, owner_id, title, messages, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run("legacy-chat", "", "Legacy", JSON.stringify([{ role: "user", content: "legacy" }]), Date.now(), Date.now());
  db.close();
}

test("resolveAppPaths keeps the explicit app-home contract stable", () => {
  const moduleRoot = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-root-"));
  const appHome = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-home-"));
  try {
    const paths = resolveAppPaths({
      moduleRoot,
      appHome,
      envAppHome: path.join(os.tmpdir(), "ignored-env-home"),
      localAppData: path.join(os.tmpdir(), "ignored-local-app-data")
    });

    assert.equal(paths.module_root, path.resolve(moduleRoot));
    assert.equal(paths.app_home, path.resolve(appHome));
    assert.equal(paths.app_dir, path.join(path.resolve(appHome), "app"));
    assert.equal(paths.config_dir, path.join(path.resolve(appHome), "config"));
    assert.equal(paths.state_dir, path.join(path.resolve(appHome), "state"));
    assert.equal(paths.log_dir, path.join(path.resolve(appHome), "logs"));
    assert.equal(paths.config_path, path.join(path.resolve(appHome), "config", "config.json"));
    assert.equal(paths.frontend_policy_path, path.join(path.resolve(appHome), "config", "frontend_policy.json"));
    assert.equal(paths.salt_path, path.join(path.resolve(appHome), "config", ".salt"));
    assert.equal(paths.chats_db_path, path.join(path.resolve(appHome), "state", "chats.db"));
  } finally {
    rmSync(moduleRoot, { recursive: true, force: true });
    rmSync(appHome, { recursive: true, force: true });
  }
});

test("resolveAppPaths uses env override, then LOCALAPPDATA, and fails hard without both", () => {
  const moduleRoot = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-order-"));
  try {
    const envPaths = resolveAppPaths({
      moduleRoot,
      envAppHome: path.join(os.tmpdir(), "vp-env-home"),
      localAppData: path.join(os.tmpdir(), "vp-local-app-data")
    });
    assert.equal(envPaths.app_home, path.resolve(path.join(os.tmpdir(), "vp-env-home")));

    const localAppData = path.join(os.tmpdir(), "vp-local-app-data");
    const localPaths = resolveAppPaths({ moduleRoot, envAppHome: "", localAppData });
    assert.equal(localPaths.app_home, path.resolve(localAppData, "Enterprise Stack", "Client Frontend"));

    assert.throws(
      () => resolveAppPaths({ moduleRoot, envAppHome: "", localAppData: "" }),
      /VISION_PIPELINE_CLIENT_FRONTEND_HOME is not set and LOCALAPPDATA is empty/
    );
  } finally {
    rmSync(moduleRoot, { recursive: true, force: true });
  }
});

test("legacy root state migrates into the external app-home layout", () => {
  const moduleRoot = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-migrate-root-"));
  const appHome = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-migrate-home-"));
  try {
    const appPaths = ensureAppHomeLayout({ moduleRoot, appHome });
    writeFileSync(path.join(moduleRoot, "config.json"), JSON.stringify({ customer_name: "Legacy Customer" }), "utf8");
    writeFileSync(path.join(moduleRoot, "frontend_policy.json"), JSON.stringify(buildDefaultFrontendPolicy()), "utf8");
    writeFileSync(path.join(moduleRoot, ".salt"), "legacy-salt", "utf8");
    mkdirSync(path.join(moduleRoot, "logs"), { recursive: true });
    writeFileSync(path.join(moduleRoot, "logs", "startup.log"), "legacy-log", "utf8");
    createLegacyChatStore(moduleRoot);

    const result = migrateLegacyRootState({ moduleRoot, appHome });

    assert.equal(result.migrated, true);
    assert.deepEqual(result.entries, ["config.json", "frontend_policy.json", ".salt", "logs", "chats.db"]);
    assert.equal(existsSync(path.join(moduleRoot, "config.json")), false);
    assert.equal(existsSync(path.join(moduleRoot, "frontend_policy.json")), false);
    assert.equal(existsSync(path.join(moduleRoot, ".salt")), false);
    assert.equal(existsSync(path.join(moduleRoot, "logs")), false);
    assert.equal(existsSync(path.join(moduleRoot, "chats.db")), false);
    assert.equal(existsSync(appPaths.config_path), true);
    assert.equal(existsSync(appPaths.frontend_policy_path), true);
    assert.equal(existsSync(appPaths.salt_path), true);
    assert.equal(existsSync(path.join(appPaths.log_dir, "startup.log")), true);
    assert.equal(existsSync(appPaths.chats_db_path), true);
  } finally {
    rmSync(moduleRoot, { recursive: true, force: true });
    rmSync(appHome, { recursive: true, force: true });
  }
});

test("state snapshots import config and state trees into the external app-home", () => {
  const moduleRoot = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-snapshot-root-"));
  const appHome = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-snapshot-home-"));
  try {
    const snapshotConfigDir = path.join(moduleRoot, "state-snapshot", "config");
    const snapshotStateDir = path.join(moduleRoot, "state-snapshot", "state");
    mkdirSync(snapshotConfigDir, { recursive: true });
    mkdirSync(snapshotStateDir, { recursive: true });
    writeFileSync(path.join(snapshotConfigDir, "config.json"), JSON.stringify({ customer_name: "Snapshot Customer" }), "utf8");
    writeFileSync(path.join(snapshotConfigDir, "frontend_policy.json"), JSON.stringify(buildDefaultFrontendPolicy()), "utf8");
    writeFileSync(path.join(snapshotConfigDir, ".salt"), "snapshot-salt", "utf8");
    writeFileSync(path.join(snapshotStateDir, "chats.db"), "snapshot-db", "utf8");

    const result = importStateSnapshot({ moduleRoot, appHome });
    const paths = resolveAppPaths({ moduleRoot, appHome });

    assert.equal(result.imported, true);
    assert.equal(existsSync(paths.config_path), true);
    assert.equal(existsSync(paths.frontend_policy_path), true);
    assert.equal(existsSync(paths.salt_path), true);
    assert.equal(existsSync(paths.chats_db_path), true);
  } finally {
    rmSync(moduleRoot, { recursive: true, force: true });
    rmSync(appHome, { recursive: true, force: true });
  }
});

test("createApplication migrates legacy root state and keeps runtime writes inside app-home", async () => {
  const fixture = createServerFixture("vp-app-home-");
  writeFrontendShell(fixture);
  writeFileSync(
    path.join(fixture.moduleRoot, "config.json"),
    JSON.stringify({
      customer_name: "Migrated Customer",
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1",
      llm_model: "gpt-4.1",
      llm_api_key: "",
      embedding_provider: "openai",
      embedding_base_url: "https://api.openai.com/v1",
      embedding_model: "text-embedding-3-small",
      embedding_api_key: "",
      port: 3000,
      theme: "dark",
      admin_secret: "",
      context_limit: 127096
    }),
    "utf8"
  );
  writeFileSync(path.join(fixture.moduleRoot, ".salt"), "legacy-salt", "utf8");
  createLegacyChatStore(fixture.moduleRoot);

  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => createStubAgent()
  });
  const baseUrl = await listen(app.server);

  try {
    const healthRes = await fetch(`${baseUrl}/api/v2/health`);
    assert.equal(healthRes.status, 200);
    const health = await healthRes.json();
    assert.equal(health.customer_name, "Migrated Customer");

    const chatRes = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Bitte pruefen" })
    });
    assert.equal(chatRes.status, 200);
    assert.equal((await chatRes.json()).answer, "Antwort auf Bitte pruefen");

    assert.equal(existsSync(path.join(fixture.moduleRoot, "config.json")), false);
    assert.equal(existsSync(path.join(fixture.moduleRoot, ".salt")), false);
    assert.equal(existsSync(path.join(fixture.moduleRoot, "chats.db")), false);
    assert.equal(existsSync(path.join(fixture.appHome, "config", "config.json")), true);
    assert.equal(existsSync(path.join(fixture.appHome, "config", "frontend_policy.json")), true);
    assert.equal(existsSync(path.join(fixture.appHome, "config", ".salt")), true);
    assert.equal(existsSync(path.join(fixture.appHome, "state", "chats.db")), true);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
