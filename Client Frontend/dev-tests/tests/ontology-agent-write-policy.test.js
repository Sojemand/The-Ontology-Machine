import assert from "node:assert/strict";
import test from "node:test";

import { assertOntologyWriteSql } from "../../client_frontend/ontology_agent/sql_write_policy.js";

test("ontology write policy allows ontology-layer writes and rejects corpus document writes", () => {
  assert.equal(assertOntologyWriteSql("INSERT INTO ontology_lenses (ontology_id, name) VALUES (?, ?)").tableName, "ontology_lenses");
  assert.equal(assertOntologyWriteSql("UPDATE source_document_pages SET page_label = ? WHERE document_id = ?").tableName, "source_document_pages");
  assert.throws(() => assertOntologyWriteSql("INSERT INTO documents (id) VALUES (?)"), /cannot write table 'documents'/);
  assert.throws(() => assertOntologyWriteSql("CREATE TABLE nope (id TEXT)"), /DDL/);
});

test("ontology write policy rejects inserts without stable object ids", () => {
  assert.throws(
    () => assertOntologyWriteSql("INSERT INTO ontology_nodes (ontology_id, node_type, canonical_label) VALUES (?, ?, ?)"),
    /Missing required column\(s\): node_id/
  );
  assert.throws(
    () => assertOntologyWriteSql("INSERT INTO ontology_assertions (ontology_id, subject_ref_type, subject_ref_id, predicate) VALUES (?, ?, ?, ?)"),
    /Missing required column\(s\): assertion_id/
  );
  assert.throws(
    () => assertOntologyWriteSql("INSERT INTO ontology_evidence_links (ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id) VALUES (?, ?, ?, ?, ?)"),
    /Missing required column\(s\): evidence_link_id/
  );
  assert.throws(
    () => assertOntologyWriteSql("INSERT INTO ontology_terms (term_id, ontology_id, label, normalized_label, term_kind) SELECT ?, ?, ?, ?, ?"),
    /must use explicit VALUES/
  );
});

test("ontology write policy rejects blank identifier values", () => {
  assert.throws(
    () => assertOntologyWriteSql(
      "INSERT INTO ontology_terms (term_id, ontology_id, label, normalized_label, term_kind) VALUES (?, ?, ?, ?, ?)",
      [null, "lens_primary", "Story Arc", "story_arc", "framework"]
    ),
    /non-empty value for term_id/
  );
  assert.throws(
    () => assertOntologyWriteSql(
      "INSERT INTO ontology_nodes (node_id, ontology_id, node_type, canonical_label) VALUES (?, ?, ?, ?)",
      ["", "lens_primary", "concept", "Story"]
    ),
    /non-empty value for node_id/
  );
  assert.throws(
    () => assertOntologyWriteSql(
      "INSERT INTO ontology_evidence_links (evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id) VALUES (?, ?, ?, ?, ?, ?)",
      [" ", "lens_primary", "node", "node_1", "document", "doc_1"]
    ),
    /non-empty value for evidence_link_id/
  );
  assert.throws(
    () => assertOntologyWriteSql(
      "INSERT INTO ontology_evidence_links (evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id) VALUES (NULL, ?, ?, ?, ?, ?)",
      ["lens_primary", "node", "node_1", "document", "doc_1"]
    ),
    /non-empty value for evidence_link_id/
  );
});
