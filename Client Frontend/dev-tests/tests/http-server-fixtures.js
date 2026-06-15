import path from "node:path";
import { DatabaseSync } from "node:sqlite";

import { createServerFixture, writeCorpusDocuments, writeFrontendConfig, writeFrontendShell } from "./server-fixtures.js";

export function createHttpServerFixture(prefix = "vp-http-", configOverrides = {}) {
  const fixture = createServerFixture(prefix, configOverrides);
  writeCorpusDocuments(fixture, `
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
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, ordinal INTEGER, is_current INTEGER DEFAULT 1);
    CREATE TABLE document_payloads (document_id TEXT PRIMARY KEY, free_text TEXT, structured_json TEXT);
    CREATE TABLE extracted_fields (document_id TEXT, key TEXT, value TEXT, value_type TEXT, numeric_value REAL);
    CREATE TABLE extracted_rows (document_id TEXT, row_index INTEGER, row_json TEXT);
    CREATE TABLE evidence_atoms (
      atom_id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id TEXT NOT NULL,
      atom_type TEXT NOT NULL,
      json_path TEXT NOT NULL,
      page INTEGER,
      source_ref TEXT,
      text_value TEXT,
      context_label TEXT,
      context_window TEXT
    );
    CREATE TABLE people (document_id TEXT, name TEXT);
    CREATE TABLE organizations (document_id TEXT, name TEXT);
    CREATE TABLE tags (document_id TEXT, tag TEXT);
    CREATE TABLE embeddings (document_id TEXT, vector BLOB, dimensions INTEGER, embedding_text TEXT);
  `, (db) => {
    db.prepare(`
      INSERT INTO documents (
        id, file_name, file_path, content_hash, document_type, category, subcategory,
        page_count, content_free_text
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      "doc-1",
      "alpha.pdf",
      "./page_images/alpha.pdf.hash",
      "sha256:doc-1",
      "invoice",
      "finance",
      "utility",
      1,
      "Strom Abschlag Januar"
    );
    db.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .run("doc-1", "title", "Title", "string", "title", "Stromrechnung Januar", 0, 1);
    db.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .run("doc-1", "billing_date", "Billing Date", "string", "date", "2024-01-10", 1, 1);
    db.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .run("doc-1", "billing_actor", "Billing Actor", "string", "actor", "Alpha GmbH", 2, 1);
    db.prepare("INSERT INTO document_payloads (document_id, free_text, structured_json) VALUES (?, ?, ?)")
      .run("doc-1", "Strom Abschlag Januar", JSON.stringify({ document_type: "invoice" }));
    db.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type, numeric_value) VALUES (?, ?, ?, ?, ?)")
      .run("doc-1", "subject", "Strom", "text", null);
    db.prepare("INSERT INTO extracted_rows (document_id, row_index, row_json) VALUES (?, ?, ?)")
      .run("doc-1", 0, JSON.stringify({ item: "Abschlag", amount: 123.45 }));
    db.prepare(`
      INSERT INTO evidence_atoms (document_id, atom_type, json_path, page, source_ref, text_value, context_label, context_window)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run("doc-1", "free_text", "content.free_text", 1, "page1_para_1", "Strom Abschlag Januar", "free_text", "Strom Abschlag Januar");
    db.prepare("INSERT INTO people (document_id, name) VALUES (?, ?)").run("doc-1", "Norman Weiss");
    db.prepare("INSERT INTO organizations (document_id, name) VALUES (?, ?)").run("doc-1", "Alpha GmbH");
    db.prepare("INSERT INTO tags (document_id, tag) VALUES (?, ?)").run("doc-1", "rechnung");
  });
  writeFrontendShell(fixture);
  writeFrontendConfig(fixture, configOverrides);
  return fixture;
}

export function createSimpleServerFixture(prefix = "vp-history-", configOverrides = {}) {
  const fixture = createServerFixture(prefix, configOverrides);
  writeCorpusDocuments(fixture, `
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
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, ordinal INTEGER, is_current INTEGER DEFAULT 1);
  `, (db) => {
    db.prepare(`
      INSERT INTO documents (
        id, file_name, file_path, content_hash, document_type, page_count, content_free_text
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run("doc-1", "alpha.pdf", "data/alpha.pdf", "sha256:aaaa", "letter", 1, "Hello");
    db.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .run("doc-1", "title", "Title", "string", "title", "Test Doc", 0, 1);
  });
  writeFrontendShell(fixture);
  writeFrontendConfig(fixture, configOverrides);
  return fixture;
}

export function insertLegacyChat(fixture) {
  const db = new DatabaseSync(path.join(fixture.moduleRoot, "chats.db"));
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

export function createStubAgent() {
  return {
    async chat({ message, history }) {
      return {
        answer: `Antwort auf ${message}`,
        sources: [{
          id: "doc-1",
          title: "Test Doc",
          type: "letter",
          date: "2024-01-10",
          actor: "Acme",
          page: 1,
          page_count: 1,
          source_refs: ["page1"],
          snippet: "Evidence",
          image_url: "/api/image/doc-1/1",
          viewer_available: false,
          file_name: "alpha.pdf",
          file_path: "C:\\secret\\alpha.pdf",
          page_images: ["C:\\secret\\page_001.png"]
        }],
        mode: "lookup",
        exactness: "evidence_grounded",
        metrics: { scope_documents: 1, matched_documents: 1, matched_occurrences: 1, aggregated_values: null },
        ambiguities: [],
        method: "stub",
        history: [...history, { role: "user", content: message }, { role: "assistant", content: `Antwort auf ${message}` }]
      };
    },
    countDocuments() {
      return 1;
    },
    resolveImage() {
      return { available: false, path: null };
    },
    close() {}
  };
}
