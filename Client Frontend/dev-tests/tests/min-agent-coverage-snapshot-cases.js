import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalRepository } from "../../client_frontend/min_agent/repository.js";
import { createCoverageFixture } from "./min-agent-coverage-fixture.js";
import {
  cleanupAgentFixture,
  createTempAgentFixture
} from "./min-agent-test-fixtures.js";

test("database_coverage_snapshot summarizes materialization surfaces without an LLM call", () => {
  const fixture = createCoverageFixture();
  const repository = createMinimalRepository({ dbPath: fixture.dbPath, dataDir: fixture.dataDir });
  try {
    const snapshot = repository.databaseCoverageSnapshot({ focus: "overview", limit: 10 });
    assert.equal(snapshot.ok, true);
    assert.equal(snapshot.database.document_count, 2);
    assert.equal(snapshot.database.page_count_total, 3);
    assert.equal(snapshot.database.page_count_basis, "documents.page_count_legacy_sum");
    assert.equal(snapshot.database.embeddings.chunk_count, 1);
    assert.equal(snapshot.materialization.active_release_id, "release_story");
    assert.equal(snapshot.materialization.mixed_release_materialization, true);
    assert.equal(snapshot.promotion_coverage.slot_count, 3);
    assert.equal(snapshot.promotion_coverage.slots.some((slot) => slot.slot === "document_themes" && slot.document_count === 2), true);
    assert.equal(snapshot.field_coverage.field_key_count, 2);
    assert.equal(snapshot.row_coverage.row_types.some((row) => row.row_type === "character_row"), true);
    assert.equal(snapshot.weak_spots.unbacked_slot_candidates[0].slot, "latent_theme");
  } finally {
    repository.close();
    cleanupAgentFixture(fixture);
  }
});

test("database_coverage_snapshot counts materialized page rows instead of repeated document page_count values", () => {
  const fixture = createTempAgentFixture("vp-min-agent-coverage-pages-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT,
      file_path TEXT,
      content_hash TEXT,
      source_document_id TEXT,
      page_index INTEGER,
      page_count INTEGER DEFAULT 1,
      source_page_count INTEGER
    );
    CREATE TABLE source_document_pages (
      source_document_id TEXT NOT NULL,
      document_id TEXT NOT NULL,
      page_index INTEGER NOT NULL,
      PRIMARY KEY (source_document_id, document_id)
    );
    CREATE TABLE structural_units (
      unit_id TEXT PRIMARY KEY,
      source_document_id TEXT NOT NULL,
      unit_type TEXT NOT NULL,
      document_id TEXT,
      page_index INTEGER
    );
  `);
  for (const sourceId of ["source-a", "source-b", "source-c"]) {
    for (let pageIndex = 0; pageIndex < 5; pageIndex += 1) {
      const docId = `${sourceId}-p${pageIndex + 1}`;
      fixture.database.prepare(
        "INSERT INTO documents (id, file_name, file_path, content_hash, source_document_id, page_index, page_count, source_page_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
      ).run(docId, `${docId}.pdf`, `${docId}.pdf`, `sha256:${docId}`, sourceId, pageIndex, 5, 5);
      fixture.database.prepare(
        "INSERT INTO source_document_pages (source_document_id, document_id, page_index) VALUES (?, ?, ?)"
      ).run(sourceId, docId, pageIndex);
      fixture.database.prepare(
        "INSERT INTO structural_units (unit_id, source_document_id, unit_type, document_id, page_index) VALUES (?, ?, ?, ?, ?)"
      ).run(`su_${docId}`, sourceId, "page_unit", docId, pageIndex);
    }
  }
  fixture.database.close();
  fixture.database = null;

  const repository = createMinimalRepository({ dbPath: fixture.dbPath, dataDir: fixture.dataDir });
  try {
    const snapshot = repository.databaseCoverageSnapshot({ focus: "overview", limit: 5 });
    assert.equal(snapshot.ok, true);
    assert.equal(snapshot.database.document_count, 15);
    assert.equal(snapshot.database.page_count_total, 15);
    assert.equal(snapshot.database.page_count_basis, "source_document_pages");
  } finally {
    repository.close();
    cleanupAgentFixture(fixture);
  }
});

test("database_coverage_snapshot tolerates minimal corpus schemas", () => {
  const fixture = createTempAgentFixture("vp-min-agent-coverage-minimal-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT,
      file_path TEXT,
      content_hash TEXT,
      page_count INTEGER DEFAULT 1
    );
  `);
  fixture.database.prepare("INSERT INTO documents (id, file_name, file_path, content_hash, page_count) VALUES (?, ?, ?, ?, ?)")
    .run("doc-min", "minimal.pdf", "C:\\artifact\\minimal.pdf", "sha256:minimal", 1);
  fixture.database.close();
  fixture.database = null;

  const repository = createMinimalRepository({ dbPath: fixture.dbPath, dataDir: fixture.dataDir });
  try {
    const snapshot = repository.databaseCoverageSnapshot({ focus: "weak_spots", limit: 5 });
    assert.equal(snapshot.ok, true);
    assert.equal(snapshot.database.document_count, 1);
    assert.equal(snapshot.availability.document_promotions, false);
    assert.equal(snapshot.weak_spots.documents_with_low_promotions[0].promotion_count, 0);
  } finally {
    repository.close();
    cleanupAgentFixture(fixture);
  }
});
