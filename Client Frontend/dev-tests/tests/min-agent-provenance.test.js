import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalAgent } from "../../server/min_agent.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture, insertDocument } from "./min-agent-test-fixtures.js";

test("get_provenance exposes normalized-first field matches and linked evidence", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-provenance-", `
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
    CREATE TABLE extracted_fields (document_id TEXT, key TEXT, value TEXT, value_type TEXT, numeric_value REAL, confidence TEXT, source TEXT, normalized_value TEXT, compact_value TEXT);
    CREATE TABLE slot_candidates (candidate_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, display_value TEXT, strategy TEXT, confidence REAL, is_projection_backed INTEGER, origin_path TEXT, source_refs_json TEXT);
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, normalized_value TEXT, compact_value TEXT, ordinal INTEGER, confidence REAL, candidate_id INTEGER, source_path TEXT, projection_id TEXT, release_fingerprint TEXT, is_current INTEGER DEFAULT 1);
    CREATE TABLE candidate_evidence (candidate_id INTEGER, atom_id INTEGER);
    CREATE TABLE evidence_atoms (atom_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL, atom_type TEXT NOT NULL, json_path TEXT NOT NULL, page INTEGER, source_ref TEXT, text_value TEXT, context_label TEXT, context_window TEXT);
  `);

  insertDocument(fixture.database, {
    id: "doc-prov",
    file_name: "prov.pdf",
    file_path: "page_images/prov.pdf.hash",
    content_hash: "sha256:provhash",
    document_type: "advance_payment",
    subcategory: "advance_payment_adjustment",
    content_free_text: "advance_payment finance",
    promotions: []
  });
  fixture.database.prepare("INSERT INTO extracted_fields (document_id, key, value, value_type, numeric_value, confidence, source, normalized_value, compact_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-prov", "subject", "Informationsschreiben", "text", null, "unconfirmed", "vision", "informationsschreiben", "informationsschreiben");
  const candidateResult = fixture.database.prepare("INSERT INTO slot_candidates (document_id, slot, display_value, strategy, confidence, is_projection_backed, origin_path, source_refs_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-prov", "subject", "Informationsschreiben", "projection_candidate:field", 10, 1, "content.fields.subject", "[\"page1_para_3\"]");
  const atomResult = fixture.database.prepare("INSERT INTO evidence_atoms (document_id, atom_type, json_path, page, source_ref, text_value, context_label, context_window) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-prov", "field", "content.fields.subject", 1, "page1_para_3", "Informationsschreiben", "subject", "Informationsschreiben");
  fixture.database.prepare("INSERT INTO candidate_evidence (candidate_id, atom_id) VALUES (?, ?)").run(candidateResult.lastInsertRowid, atomResult.lastInsertRowid);
  fixture.database.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, normalized_value, compact_value, ordinal, confidence, candidate_id, source_path, projection_id, release_fingerprint, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-prov", "subject", "Betreff", "string", "title", "Informationsschreiben", "informationsschreiben", "informationsschreiben", 0, 1, candidateResult.lastInsertRowid, "content.fields.subject", "housing.custom.v1", "sha256:test", 1);
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
              tool_calls: [{ id: "tool-get-provenance", type: "function", function: { name: "get_provenance", arguments: JSON.stringify({ doc_id: "doc-prov", target: "subject", target_kind: "promotion" }) } }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Provenance geprueft.", tool_calls: [] } }] };
    }
  });

  try {
    await agent.chat({ message: "Woher kommt der Betreff?" });
    const toolPayload = JSON.parse(String(calls[1].find((message) => message.role === "tool")?.content || "{}"));
    assert.equal(toolPayload.doc_id, "doc-prov");
    assert.equal(toolPayload.target, "subject");
    assert.equal(toolPayload.layer_info.active_sql_layer, "normalized_first");
    assert.equal(toolPayload.layer_info.active_value_layer, "document_promotions");
    assert.equal(toolPayload.active_value, "Informationsschreiben");
    assert.equal(toolPayload.document_promotions.some((promotion) => promotion.slot === "subject" && promotion.source_path === "content.fields.subject"), true);
    assert.equal(toolPayload.fields.length, 0);
    assert.equal(toolPayload.slot_candidates.some((candidate) => candidate.slot === "subject"), true);
    assert.equal(toolPayload.linked_evidence_atoms.some((atom) => atom.source_ref === "page1_para_3"), true);
    assert.equal(toolPayload.direct_evidence_atoms.some((atom) => atom.context_label === "subject"), true);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
