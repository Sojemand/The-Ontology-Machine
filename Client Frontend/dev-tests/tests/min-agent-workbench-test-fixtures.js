import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";

import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

const PROJECT_ROOT = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));

function relativeRuntimePath(rootDir, targetPath) {
  return path.relative(rootDir, targetPath).split(path.sep).join("/");
}

export function writeRuntimeManifest(rootDir, { runtimeBacked = false } = {}) {
  const runtimeDir = path.join(rootDir, "runtime");
  const manifest = runtimeBacked
    ? {
      node: ["node/node.exe"],
      python: [relativeRuntimePath(rootDir, path.join(PROJECT_ROOT, "runtime", "python", "python.exe"))],
      powershell: [relativeRuntimePath(rootDir, path.join(PROJECT_ROOT, "runtime", "powershell", "powershell.exe"))]
    }
    : {
      node: ["node/node.exe"],
      python: ["runtime/python/python.exe", "runtime/python/Scripts/python.exe", "runtime/python/bin/python"],
      powershell: ["runtime/powershell/pwsh.exe", "runtime/powershell/powershell.exe", "runtime/powershell/pwsh/pwsh.exe"]
    };
  mkdirSync(runtimeDir, { recursive: true });
  writeFileSync(path.join(runtimeDir, "runtime-manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
}

export function createWorkbenchFixture({ runtimeBacked = false } = {}) {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-min-wb-"));
  const dataDir = path.join(rootDir, "active-corpus");
  const assistantDir = path.join(rootDir, "assistant");
  mkdirSync(dataDir, { recursive: true });
  mkdirSync(assistantDir, { recursive: true });
  writeRuntimeManifest(rootDir, { runtimeBacked });
  writeFileSync(path.join(rootDir, "config.json"), JSON.stringify({ ok: true }), "utf8");
  writeFileSync(path.join(rootDir, "frontend_policy.json"), JSON.stringify(buildDefaultFrontendPolicy()), "utf8");
  writeFileSync(path.join(assistantDir, "soul.txt"), "Name: TestBot", "utf8");
  writeFileSync(path.join(dataDir, "notes.txt"), "allowed note", "utf8");

  const dbPath = path.join(dataDir, "corpus.db");
  const db = new DatabaseSync(dbPath);
  db.exec(`
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      page_count INTEGER DEFAULT 1,
      content_free_text TEXT
    );
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, ordinal INTEGER, is_current INTEGER DEFAULT 1);
  `);
  db.prepare(`
    INSERT INTO documents (id, file_name, file_path, content_hash, page_count, content_free_text)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run("doc-1", "alpha.pdf", "active-corpus/alpha.pdf", "sha256:aaaa", 1, "Text");
  db.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "title", "Title", "string", "title", "Alpha", 0, 1);
  db.close();

  return { rootDir, dataDir, dbPath };
}

export function cleanupWorkbenchFixture(rootDir) {
  rmSync(rootDir, { recursive: true, force: true });
}
