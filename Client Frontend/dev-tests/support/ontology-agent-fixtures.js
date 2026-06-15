import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

import { createOntologyRepository } from "../../client_frontend/ontology_agent/repository.js";

import { ONTOLOGY_TEST_SCHEMA } from "./ontology-agent-schema.js";

export function createFixture() {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-ontology-agent-"));
  const dataDir = path.join(tempDir, "data");
  const dbPath = path.join(dataDir, "corpus.db");
  mkdirSync(dataDir, { recursive: true });
  const database = new DatabaseSync(dbPath);
  database.exec(ONTOLOGY_TEST_SCHEMA);
  database.prepare("INSERT INTO documents (id, file_name, file_path, content_hash, document_type, page_count, content_free_text) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "alpha.pdf", "alpha.pdf", "sha256:doc-1", "recipe", 1, "Lazy pasta with tomato sauce");
  database.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "title", "Title", "string", "title", "Lazy pasta", 0, 1);
  database.close();
  return { tempDir, dataDir, dbPath };
}

export function cleanupFixture(fixture) {
  rmSync(fixture.tempDir, { recursive: true, force: true });
}

export function createRepository(fixture, overrides = {}) {
  return createOntologyRepository({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    getRuntimeConfig: () => ({ embedding_model: "test-embedding" }),
    embedTextsFn: async (_runtimeConfig, texts) => texts.map(() => [0.1, 0.2]),
    validatePatchFn: async () => ({ status: "pass", checks: [], warnings: [], errors: [] }),
    ...overrides
  });
}
