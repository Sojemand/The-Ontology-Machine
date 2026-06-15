import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

export const DOCUMENTS_TABLE_SQL = `
  CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    document_type TEXT,
    category TEXT,
    subcategory TEXT,
    page_count INTEGER DEFAULT 1,
    content_free_text TEXT
  );
  CREATE TABLE document_promotions (
    promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    slot TEXT,
    slot_label TEXT,
    value_type TEXT,
    query_role TEXT,
    display_value TEXT,
    normalized_value TEXT,
    compact_value TEXT,
    ordinal INTEGER,
    confidence REAL,
    candidate_id INTEGER,
    source_path TEXT,
    projection_id TEXT,
    release_fingerprint TEXT,
    is_current INTEGER DEFAULT 1
  );
`;

export function createTempAgentFixture(prefix, schemaSql = DOCUMENTS_TABLE_SQL) {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), prefix));
  const dataDir = path.join(tempDir, "data");
  const dbPath = path.join(dataDir, "corpus.db");
  mkdirSync(dataDir, { recursive: true });
  const database = new DatabaseSync(dbPath);
  if (schemaSql) {
    database.exec(schemaSql);
  }
  return { tempDir, dataDir, dbPath, database };
}

export function cleanupAgentFixture(fixture) {
  if (fixture?.database) {
    try {
      fixture.database.close();
    } catch {}
  }
  rmSync(fixture.tempDir, { recursive: true, force: true });
}

export function createRuntimeConfig(overrides = {}) {
  return {
    llm_model: "gpt-5.4-mini",
    context_limit: 60096,
    llm_api_key: "",
    embedding_api_key: "",
    ...overrides
  };
}

export function insertDocument(database, overrides = {}) {
  const document = {
    id: "doc-1",
    file_name: "alpha.pdf",
    file_path: "page_images/alpha.pdf.hash",
    content_hash: "sha256:aaaaaaaa",
    document_type: "invoice",
    category: "finance",
    subcategory: "utility",
    page_count: 1,
    content_free_text: "Strom Abschlag Januar",
    promotions: [
      { slot: "title", slot_label: "Title", query_role: "title", display_value: "Stromrechnung Januar", ordinal: 0 },
      { slot: "billing_date", slot_label: "Billing Date", query_role: "date", display_value: "2024-01-10", ordinal: 1 },
      { slot: "billing_actor", slot_label: "Billing Actor", query_role: "actor", display_value: "Alpha GmbH", ordinal: 2 }
    ],
    ...overrides
  };
  database.prepare(`
    INSERT INTO documents (
      id, file_name, file_path, content_hash, document_type, category, subcategory,
      page_count, content_free_text
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    document.id,
    document.file_name,
    document.file_path,
    document.content_hash,
    document.document_type,
    document.category,
    document.subcategory,
    document.page_count,
    document.content_free_text
  );
  for (const promotion of document.promotions || []) {
    insertDocumentPromotion(database, { document_id: document.id, ...promotion });
  }
}

export function insertDocumentPromotion(database, overrides = {}) {
  const promotion = {
    document_id: "doc-1",
    slot: "title",
    slot_label: "Title",
    value_type: "string",
    query_role: "title",
    display_value: "Stromrechnung Januar",
    normalized_value: null,
    compact_value: null,
    ordinal: 0,
    confidence: 1,
    candidate_id: null,
    source_path: "content.fields.title",
    projection_id: "test.dynamic.v1",
    release_fingerprint: "sha256:test",
    is_current: 1,
    ...overrides
  };
  database.prepare(`
    INSERT INTO document_promotions (
      document_id, slot, slot_label, value_type, query_role, display_value,
      normalized_value, compact_value, ordinal, confidence, candidate_id,
      source_path, projection_id, release_fingerprint, is_current
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    promotion.document_id,
    promotion.slot,
    promotion.slot_label,
    promotion.value_type,
    promotion.query_role,
    promotion.display_value,
    promotion.normalized_value,
    promotion.compact_value,
    promotion.ordinal,
    promotion.confidence,
    promotion.candidate_id,
    promotion.source_path,
    promotion.projection_id,
    promotion.release_fingerprint,
    promotion.is_current
  );
}

export function insertDocumentPageImage(database, overrides = {}) {
  const image = {
    document_id: "doc-1",
    page: 1,
    content_type: "image/png",
    image_blob: Buffer.from([0x89, 0x50, 0x4e, 0x47]),
    ...overrides
  };
  database.prepare(`
    INSERT INTO document_page_images (document_id, page, content_type, image_blob)
    VALUES (?, ?, ?, ?)
  `).run(image.document_id, image.page, image.content_type, image.image_blob);
  return image;
}
