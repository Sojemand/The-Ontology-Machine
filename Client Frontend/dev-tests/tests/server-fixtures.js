import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

export function createServerFixture(prefix = "vp-server-", configOverrides = {}) {
  const moduleRoot = mkdtempSync(path.join(os.tmpdir(), prefix));
  const appHome = mkdtempSync(path.join(os.tmpdir(), `${prefix}home-`));
  const corpusRoot = mkdtempSync(path.join(os.tmpdir(), `${prefix}corpus-`));
  const dataDir = corpusRoot;
  const appDir = path.join(moduleRoot, "app");
  const assistantDir = path.join(moduleRoot, "assistant");
  const configDir = path.join(appHome, "config");
  const stateDir = path.join(appHome, "state");
  const logDir = path.join(appHome, "logs");
  const dbPath = path.join(corpusRoot, "corpus.db");

  mkdirSync(appDir, { recursive: true });
  mkdirSync(assistantDir, { recursive: true });
  mkdirSync(configDir, { recursive: true });
  mkdirSync(stateDir, { recursive: true });
  mkdirSync(logDir, { recursive: true });

  return { moduleRoot, appHome, corpusRoot, dataDir, appDir, assistantDir, configDir, stateDir, logDir, dbPath };
}

export function writeFrontendConfig(fixture, overrides = {}) {
  writeFileSync(
    path.join(fixture.configDir, "config.json"),
    JSON.stringify({
      customer_name: "Test Customer",
      sql_database_path: fixture.dbPath,
      pipeline_root: "",
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1",
      llm_model: "gpt-5.4",
      llm_api_key: "",
      embedding_provider: "openai",
      embedding_base_url: "https://api.openai.com/v1",
      embedding_model: "text-embedding-3-small",
      embedding_api_key: "",
      port: 3000,
      theme: "dark",
      admin_secret: "",
      ...overrides
    }),
    "utf8"
  );
}

export function writeFrontendPolicy(fixture, overrides = {}) {
  writeFileSync(
    path.join(fixture.configDir, "frontend_policy.json"),
    JSON.stringify({ ...buildDefaultFrontendPolicy(), ...overrides }),
    "utf8"
  );
}

export function writeFrontendShell(fixture, soulText = "Name: TestBot\nStil: Direkt") {
  writeFileSync(path.join(fixture.appDir, "index.html"), "<html><body>Main</body></html>");
  writeFileSync(path.join(fixture.appDir, "config.html"), "<html><body>Config</body></html>");
  writeFileSync(path.join(fixture.assistantDir, "soul.txt"), soulText);
}

export function writeCorpusDocuments(fixture, schemaSql, seed) {
  const db = new DatabaseSync(fixture.dbPath);
  db.exec(schemaSql);
  seed(db);
  db.close();
}

export async function listen(server) {
  await new Promise((resolve, reject) => {
    server.listen(0, "127.0.0.1", (error) => (error ? reject(error) : resolve(undefined)));
  });
  return `http://127.0.0.1:${server.address().port}`;
}

export function extractCookie(response) {
  const cookieHeaders =
    typeof response.headers.getSetCookie === "function"
      ? response.headers.getSetCookie()
      : response.headers.get("set-cookie")
        ? [response.headers.get("set-cookie")]
        : [];
  return cookieHeaders
    .map((value) => value.split(";")[0])
    .filter(Boolean)
    .join("; ");
}

export function mergeCookies(...cookieHeaders) {
  const pairs = new Map();
  for (const header of cookieHeaders) {
    for (const part of String(header || "").split(";")) {
      const trimmed = part.trim();
      if (!trimmed) continue;
      const separatorIndex = trimmed.indexOf("=");
      if (separatorIndex < 0) continue;
      pairs.set(trimmed.slice(0, separatorIndex), trimmed.slice(separatorIndex + 1));
    }
  }
  return Array.from(pairs.entries()).map(([name, value]) => `${name}=${value}`).join("; ");
}

export function cleanupFixture(fixture) {
  rmSync(fixture.moduleRoot, { recursive: true, force: true });
  rmSync(fixture.appHome, { recursive: true, force: true });
  rmSync(fixture.corpusRoot, { recursive: true, force: true });
}
