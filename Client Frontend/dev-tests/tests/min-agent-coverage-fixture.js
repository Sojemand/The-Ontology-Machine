import {
  DOCUMENTS_TABLE_SQL,
  createTempAgentFixture,
  insertDocument
} from "./min-agent-test-fixtures.js";

export const COVERAGE_TABLES_SQL = `
  CREATE TABLE document_payloads (
    document_id TEXT PRIMARY KEY,
    structured_json TEXT,
    normalized_json TEXT,
    projection_json TEXT,
    release_fingerprint TEXT
  );
  CREATE TABLE extracted_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT DEFAULT 'text'
  );
  CREATE TABLE extracted_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    row_json TEXT NOT NULL
  );
  CREATE TABLE slot_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    display_value TEXT NOT NULL,
    is_projection_backed INTEGER DEFAULT 0
  );
  CREATE TABLE embedding_chunks (
    document_id TEXT,
    vector BLOB,
    dimensions INTEGER,
    chunk_text TEXT
  );
  CREATE TABLE embeddings (
    document_id TEXT,
    vector BLOB,
    dimensions INTEGER,
    embedding_text TEXT
  );
  CREATE TABLE installation_state (
    singleton INTEGER PRIMARY KEY,
    active_release_id TEXT,
    active_release_version TEXT,
    active_release_fingerprint TEXT,
    active_snapshot_id TEXT,
    master_taxonomy_id TEXT,
    master_taxonomy_version TEXT,
    runtime_locale TEXT,
    integrity_status TEXT,
    materialization_version TEXT
  );
  CREATE TABLE document_processing_state (
    document_id TEXT PRIMARY KEY,
    materialization_state TEXT,
    projection_id TEXT
  );
  CREATE TABLE materialization_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT,
    code TEXT
  );
`;

export function createCoverageFixture(prefix = "vp-min-agent-coverage-") {
  const fixture = createTempAgentFixture(prefix, `${DOCUMENTS_TABLE_SQL}${COVERAGE_TABLES_SQL}`);
  populateCoverageFixture(fixture.database);
  fixture.database.close();
  fixture.database = null;
  return fixture;
}

export function populateCoverageFixture(database) {
  insertCoverageDocuments(database);
  insertCoveragePayloads(database);
  insertCoverageFieldsAndRows(database);
  insertCoverageRuntimeState(database);
}

function insertCoverageDocuments(database) {
  insertDocument(database, {
    id: "doc-1",
    file_name: "fantasy-a.pdf",
    file_path: "page_images/fantasy-a.hash",
    content_hash: "sha256:fantasy-a",
    document_type: "story",
    category: "fiction",
    subcategory: "fantasy",
    page_count: 1,
    content_free_text: "A city, a captain and a seal.",
    promotions: [
      { slot: "story_title", slot_label: "Story Title", query_role: "title", display_value: "The Glass Seal", ordinal: 0, release_fingerprint: "sha256:rel-a" },
      { slot: "document_themes", slot_label: "Themes", query_role: "secondary", display_value: "loyalty", ordinal: 1, release_fingerprint: "sha256:rel-a" },
      { slot: "main_character", slot_label: "Main Character", query_role: "actor", display_value: "Captain Iva", ordinal: 2, release_fingerprint: "sha256:rel-a" }
    ]
  });
  insertDocument(database, {
    id: "doc-2",
    file_name: "fantasy-b.pdf",
    file_path: "page_images/fantasy-b.hash",
    content_hash: "sha256:fantasy-b",
    document_type: "other",
    category: "other",
    subcategory: "other",
    page_count: 2,
    content_free_text: "A forest scene with a hidden oath.",
    promotions: [
      { slot: "document_themes", slot_label: "Themes", query_role: "secondary", display_value: "oath", ordinal: 0, release_fingerprint: "sha256:rel-b" }
    ]
  });
}

function insertCoveragePayloads(database) {
  database.prepare("INSERT INTO document_payloads (document_id, structured_json, normalized_json, projection_json, release_fingerprint) VALUES (?, ?, ?, ?, ?)")
    .run("doc-1", "{}", "{}", "{}", "sha256:rel-a");
  database.prepare("INSERT INTO document_payloads (document_id, structured_json, normalized_json, projection_json, release_fingerprint) VALUES (?, ?, ?, ?, ?)")
    .run("doc-2", "{}", "{}", "{}", "sha256:rel-b");
}

function insertCoverageFieldsAndRows(database) {
  database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type) VALUES (?, ?, ?, ?)")
    .run("doc-1", "setting", "city", "string");
  database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type) VALUES (?, ?, ?, ?)")
    .run("doc-2", "setting", "forest", "string");
  database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type) VALUES (?, ?, ?, ?)")
    .run("doc-2", "conflict", "oath", "string");
  database.prepare("INSERT INTO extracted_rows (document_id, row_index, row_json) VALUES (?, ?, ?)")
    .run("doc-1", 0, JSON.stringify({ _row_type: "character_row", character_name: "Captain Iva", role: "lead" }));
  database.prepare("INSERT INTO extracted_rows (document_id, row_index, row_json) VALUES (?, ?, ?)")
    .run("doc-2", 0, JSON.stringify({ _row_type: "plot_event_row", event_sequence: "1", event_description: "Oath discovered" }));
  database.prepare("INSERT INTO slot_candidates (document_id, slot, display_value, is_projection_backed) VALUES (?, ?, ?, ?)")
    .run("doc-2", "latent_theme", "betrayal", 0);
}

function insertCoverageRuntimeState(database) {
  database.prepare("INSERT INTO embedding_chunks (document_id, vector, dimensions, chunk_text) VALUES (?, ?, ?, ?)")
    .run("doc-1", Buffer.from(new Float32Array([1, 0]).buffer), 2, "city captain seal");
  database.prepare("INSERT INTO embeddings (document_id, vector, dimensions, embedding_text) VALUES (?, ?, ?, ?)")
    .run("doc-1", Buffer.from(new Float32Array([1, 0]).buffer), 2, "city captain seal");
  database.prepare("INSERT INTO installation_state (singleton, active_release_id, active_release_version, active_release_fingerprint, active_snapshot_id, master_taxonomy_id, master_taxonomy_version, runtime_locale, integrity_status, materialization_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run(1, "release_story", "custom.v1", "sha256:rel-a", "snap-1", "taxonomy_story", "custom.v1", "en", "ok", "dynamic.v1");
  database.prepare("INSERT INTO document_processing_state (document_id, materialization_state, projection_id) VALUES (?, ?, ?)")
    .run("doc-1", "current", "story_projection");
  database.prepare("INSERT INTO document_processing_state (document_id, materialization_state, projection_id) VALUES (?, ?, ?)")
    .run("doc-2", "current", "story_projection");
  database.prepare("INSERT INTO materialization_audit (level, code) VALUES (?, ?)")
    .run("warning", "unbacked_slot_candidate");
}
