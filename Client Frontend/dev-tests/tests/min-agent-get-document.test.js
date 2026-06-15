import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalAgent } from "../../server/min_agent.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture, insertDocument } from "./min-agent-test-fixtures.js";

test("get_document exposes dual-layer excerpts and provenance-aware field metadata", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-document-", `
    ${`
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
    `}
    CREATE TABLE document_payloads (document_id TEXT PRIMARY KEY, free_text TEXT, normalized_json TEXT, structured_json TEXT, projection_json TEXT);
    CREATE TABLE extracted_fields (document_id TEXT, key TEXT, value TEXT, value_type TEXT, numeric_value REAL, confidence TEXT, source TEXT, normalized_value TEXT, compact_value TEXT);
    CREATE TABLE extracted_rows (document_id TEXT, row_index INTEGER, row_json TEXT);
    CREATE TABLE evidence_atoms (atom_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL, atom_type TEXT NOT NULL, json_path TEXT NOT NULL, page INTEGER, source_ref TEXT, text_value TEXT, context_label TEXT, context_window TEXT);
    CREATE TABLE people (document_id TEXT, name TEXT);
    CREATE TABLE organizations (document_id TEXT, name TEXT);
    CREATE TABLE tags (document_id TEXT, tag TEXT);
    CREATE TABLE slot_candidates (candidate_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, display_value TEXT, strategy TEXT, confidence REAL, is_projection_backed INTEGER, origin_path TEXT);
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, normalized_value TEXT, compact_value TEXT, ordinal INTEGER, confidence REAL, candidate_id INTEGER, source_path TEXT, projection_id TEXT, release_fingerprint TEXT, is_current INTEGER DEFAULT 1);
  `);

  insertDocument(fixture.database, {
    document_type: "advance_payment",
    subcategory: "advance_payment_adjustment",
    content_free_text: "advance_payment finance",
    promotions: []
  });
  fixture.database.prepare("INSERT INTO document_payloads (document_id, free_text, normalized_json, structured_json, projection_json) VALUES (?, ?, ?, ?, ?)")
    .run("doc-1", "advance_payment finance", JSON.stringify({ content: { fields: { subject: "Informationsschreiben", recipient: "Norman Weiss" } } }), JSON.stringify({ content: { fields: { amount_reference: "3,46 € pro Quadratmeter" } } }), JSON.stringify({ candidates: [{ slot: "subject" }] }));
  fixture.database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type, numeric_value, confidence, source, normalized_value, compact_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "subject", "Informationsschreiben", "text", null, "unconfirmed", "vision", "informationsschreiben", "informationsschreiben");
  fixture.database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type, numeric_value, confidence, source, normalized_value, compact_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "amount_reference", "3,46 € pro Quadratmeter", "text", null, "confirmed", "ocr_confirmed", "3 46 pro quadratmeter", "346proquadratmeter");
  fixture.database.prepare("INSERT INTO evidence_atoms (document_id, atom_type, json_path, page, source_ref, text_value, context_label, context_window) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "field", "content.fields.amount_reference", 1, "page1_para_7", "3,46 € pro Quadratmeter", "amount_reference", "3,46 € pro Quadratmeter");
  fixture.database.prepare("INSERT INTO people (document_id, name) VALUES (?, ?)").run("doc-1", "Norman Weiss");
  fixture.database.prepare("INSERT INTO organizations (document_id, name) VALUES (?, ?)").run("doc-1", "NOVIUM Hausverwaltungs GmbH");
  fixture.database.prepare("INSERT INTO tags (document_id, tag) VALUES (?, ?)").run("doc-1", "Betriebskosten");
  fixture.database.prepare("INSERT INTO slot_candidates (document_id, slot, display_value, strategy, confidence, is_projection_backed, origin_path) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "subject", "Informationsschreiben", "projection_candidate:field", 10, 1, "content.fields.subject");
  fixture.database.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, normalized_value, compact_value, ordinal, confidence, candidate_id, source_path, projection_id, release_fingerprint, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "subject", "Betreff", "string", "title", "Informationsschreiben", "informationsschreiben", "informationsschreiben", 0, 1, null, "content.fields.subject", "housing.custom.v1", "sha256:test", 1);
  fixture.database.close();
  fixture.database = null;

  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{ id: "tool-get-document", type: "function", function: { name: "get_document", arguments: JSON.stringify({ doc_id: "doc-1" }) } }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Dokument geprueft.", tool_calls: [] } }] };
    }
  });

  try {
    await agent.chat({ message: "Pruef das Dokument" });
    const toolPayload = JSON.parse(String(calls[1].find((message) => message.role === "tool")?.content || "{}"));
    assert.equal(toolPayload.layer_info.active_sql_layer, "normalized_first");
    assert.equal(toolPayload.layer_info.preferred_payload_layer, "normalized");
    assert.equal(toolPayload.layer_info.normalized_payload_available, true);
    assert.equal(toolPayload.layer_info.structured_payload_available, true);
    assert.match(toolPayload.normalized_excerpt, /"subject":"Informationsschreiben"/);
    assert.match(toolPayload.structured_excerpt, /"amount_reference":"3,46 €/);
    assert.match(toolPayload.projection_excerpt, /"slot":"subject"/);
    assert.equal(toolPayload.fields.some((field) => field.key === "subject" && field.source === "vision"), true);
    assert.equal(toolPayload.fields.some((field) => field.key === "amount_reference" && field.confidence === "confirmed"), true);
    assert.equal(toolPayload.document.title, "Informationsschreiben");
    assert.equal(toolPayload.layer_info.active_fact_surface, "document_promotions");
    assert.equal(toolPayload.document_promotions.some((promotion) => promotion.slot === "subject" && promotion.query_role === "title"), true);
    assert.equal(toolPayload.slot_candidates.some((candidate) => candidate.slot === "subject"), true);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("compact document views keep sources linkable and expose source-document context", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-document-view-", `
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
    CREATE TABLE document_payloads (document_id TEXT PRIMARY KEY, free_text TEXT, normalized_json TEXT, structured_json TEXT, projection_json TEXT);
    CREATE TABLE extracted_fields (document_id TEXT, key TEXT, value TEXT, value_type TEXT, numeric_value REAL, confidence TEXT, source TEXT, normalized_value TEXT, compact_value TEXT);
    CREATE TABLE extracted_rows (document_id TEXT, row_index INTEGER, row_json TEXT);
    CREATE TABLE evidence_atoms (atom_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL, atom_type TEXT NOT NULL, json_path TEXT NOT NULL, page INTEGER, source_ref TEXT, text_value TEXT, context_label TEXT, context_window TEXT);
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, normalized_value TEXT, compact_value TEXT, ordinal INTEGER, confidence REAL, candidate_id INTEGER, source_path TEXT, projection_id TEXT, release_fingerprint TEXT, is_current INTEGER DEFAULT 1);
    CREATE TABLE source_documents (source_document_id TEXT PRIMARY KEY, source_uri TEXT, source_title TEXT, source_kind TEXT, page_count INTEGER, first_document_id TEXT, last_document_id TEXT, source_content_hash TEXT);
    CREATE TABLE source_document_pages (source_document_id TEXT, document_id TEXT, page_index INTEGER, page_label TEXT, confidence REAL);
    CREATE TABLE source_document_classifications (source_document_id TEXT, classification_scope TEXT, ontology_id TEXT, document_type TEXT, category TEXT, subcategory TEXT, confidence REAL, status TEXT, basis_json TEXT, created_by TEXT);
    CREATE TABLE structural_units (unit_id TEXT PRIMARY KEY, source_document_id TEXT, unit_type TEXT, document_id TEXT, page_index INTEGER, ordinal INTEGER, label TEXT, unit_origin TEXT, confidence REAL, status TEXT);
  `);

  insertDocument(fixture.database, {
    document_type: "news_article",
    category: "public_broadcast",
    subcategory: "investigative",
    content_free_text: "Short visible text",
    promotions: []
  });
  fixture.database.prepare("INSERT INTO document_payloads (document_id, free_text, normalized_json, structured_json, projection_json) VALUES (?, ?, ?, ?, ?)")
    .run("doc-1", "Short visible text", JSON.stringify({ repeated: "x".repeat(2_000) }), JSON.stringify({ rows: [{ item: "A" }] }), JSON.stringify({ projection: "news.custom" }));
  fixture.database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type, numeric_value, confidence, source, normalized_value, compact_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "topic", "location data trade", "text", null, "confirmed", "normalizer", "location data trade", "locationdatatrade");
  fixture.database.prepare("INSERT INTO extracted_rows (document_id, row_index, row_json) VALUES (?, ?, ?)")
    .run("doc-1", 0, JSON.stringify({ claim: "police bought location data" }));
  fixture.database.prepare("INSERT INTO evidence_atoms (document_id, atom_type, json_path, page, source_ref, text_value, context_label, context_window) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "field", "content.topic", 1, "page1_para_1", "location data trade", "topic", "location data trade");
  fixture.database.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, confidence, source_path, projection_id, release_fingerprint, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-1", "title", "Title", "string", "title", "Location data trade", 0, 1, "content.title", "news.custom.v1", "sha256:test", 1);
  fixture.database.prepare("INSERT INTO source_documents (source_document_id, source_uri, source_title, source_kind, page_count, first_document_id, last_document_id, source_content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("src-1", "corpus://source/src-1", "Location data report", "article", 1, "doc-1", "doc-1", "sha256:source");
  fixture.database.prepare("INSERT INTO source_document_pages (source_document_id, document_id, page_index, page_label, confidence) VALUES (?, ?, ?, ?, ?)")
    .run("src-1", "doc-1", 0, "1", 1);
  fixture.database.prepare("INSERT INTO source_document_classifications (source_document_id, classification_scope, ontology_id, document_type, category, subcategory, confidence, status, basis_json, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("src-1", "base", null, "news_article", "public_broadcast", "investigative", 1, "materialized", "{}", "basic_relation_mining");
  fixture.database.prepare("INSERT INTO structural_units (unit_id, source_document_id, unit_type, document_id, page_index, ordinal, label, unit_origin, confidence, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("unit-page-1", "src-1", "page_unit", "doc-1", 0, 1, "page 1", "base_graph", 1, "materialized");
  fixture.database.close();
  fixture.database = null;

  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{ id: "tool-get-document-view", type: "function", function: { name: "get_document_ontology_evidence", arguments: JSON.stringify({ doc_id: "doc-1" }) } }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Evidence view checked.", tool_calls: [] } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Inspect ontology evidence" });
    const toolPayload = JSON.parse(String(calls[1].find((message) => message.role === "tool")?.content || "{}"));
    assert.equal(result.sources.length, 1);
    assert.equal(result.sources[0].id, "doc-1");
    assert.equal(toolPayload.document_view, "ontology_evidence");
    assert.equal(toolPayload.source_document_context.source_document.source_document_id, "src-1");
    assert.equal(toolPayload.source_document_context.classifications[0].classification_scope, "base");
    assert.equal(toolPayload.structural_units[0].unit_type, "page_unit");
    assert.equal(toolPayload.fields[0].key, "topic");
    assert.equal(toolPayload.rows[0].row_index, 0);
    assert.ok(toolPayload.normalized_excerpt.length < 1_900);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
