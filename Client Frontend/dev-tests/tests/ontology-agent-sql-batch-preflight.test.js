import assert from "node:assert/strict";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { cleanupFixture, createFixture, createRepository } from "../support/ontology-agent-fixtures.js";

test("sql_batch_execute explains that active belongs in ontology_activation", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_bad_status",
      edit_summary: "Create lens with wrong lifecycle status",
      statements: [
        {
          sql: "INSERT INTO ontology_lenses (ontology_id, name, status) VALUES (?, ?, ?)",
          params: ["lens_bad_status", "Bad Status Lens", "active"]
        }
      ]
    });

    assert.equal(result.ok, false);
    assert.match(result.error, /CHECK constraint failed/i);
    assert.match(result.hint, /ontology_lenses\.status.*draft, ready or archived/);
    assert.match(result.hint, /ontology_activation/);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_lenses WHERE ontology_id = 'lens_bad_status'").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute preflight explains ontology foreign-key write ordering", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_missing",
      edit_summary: "Create node before lens",
      statements: [
        {
          sql: "INSERT INTO ontology_nodes (node_id, ontology_id, node_type, canonical_label) VALUES (?, ?, ?, ?)",
          params: ["node_orphan", "lens_missing", "concept", "Orphan Node"]
        }
      ]
    });

    assert.equal(result.ok, false);
    assert.equal(result.error_type, "ontology_write_preflight");
    assert.equal(result.repairable, true);
    assert.match(result.error, /ontology_write_preflight/i);
    assert.match(result.hint, /ontology_lenses/);
    assert.match(JSON.stringify(result.preflight.errors), /missing_ref_target/);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_nodes WHERE node_id = 'node_orphan'").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute preflight rejects unknown insert columns before transaction", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_bad_column",
      edit_summary: "Bad timestamp column",
      statements: [
        {
          sql: "INSERT INTO ontology_lenses (ontology_id, name, CURRENT_TIMESTAMP) VALUES (?, ?, CURRENT_TIMESTAMP)",
          params: ["lens_bad_column", "Bad Column Lens"]
        }
      ]
    });

    assert.equal(result.ok, false);
    assert.equal(result.error_type, "ontology_write_preflight");
    assert.equal(result.repairable, true);
    assert.match(result.hint, /CURRENT_TIMESTAMP belongs in the VALUES expression/i);
    assert.match(JSON.stringify(result.preflight.errors), /unknown_column/);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_lenses WHERE ontology_id = 'lens_bad_column'").rows[0].count, 0);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_edit_log").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute preflight rejects ontology_edges that point at terms", async () => {
  const fixture = createFixture();
  {
    const database = new DatabaseSync(fixture.dbPath);
    database.prepare("INSERT INTO ontology_lenses (ontology_id, name) VALUES (?, ?)").run("lens_terms", "Term Endpoint Lens");
    database.prepare("INSERT INTO ontology_nodes (node_id, ontology_id, node_type, canonical_label) VALUES (?, ?, ?, ?)").run("node_story", "lens_terms", "story", "Story");
    database.prepare("INSERT INTO ontology_terms (term_id, ontology_id, label, normalized_label, term_kind) VALUES (?, ?, ?, ?, ?)").run("term_theme", "lens_terms", "Theme", "theme", "category");
    database.close();
  }
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_terms",
      edit_summary: "Bad edge endpoint",
      statements: [
        {
          sql: "INSERT INTO ontology_edges (edge_id, ontology_id, source_node_id, target_node_id, relation_type) VALUES (?, ?, ?, ?, ?)",
          params: ["edge_bad_term", "lens_terms", "node_story", "term_theme", "has_theme"]
        }
      ]
    });

    assert.equal(result.ok, false);
    assert.equal(result.error_type, "ontology_write_preflight");
    assert.match(JSON.stringify(result.preflight.errors), /term_used_as_node/);
    assert.match(result.hint, /ontology_node/);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_edges WHERE edge_id = 'edge_bad_term'").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute preflight rejects explicit NULL in required JSON columns", async () => {
  const fixture = createFixture();
  {
    const database = new DatabaseSync(fixture.dbPath);
    database.prepare("INSERT INTO ontology_lenses (ontology_id, name) VALUES (?, ?)").run("lens_json", "JSON Lens");
    database.close();
  }
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_json",
      edit_summary: "Bad node JSON",
      statements: [
        {
          sql: "INSERT INTO ontology_nodes (node_id, ontology_id, node_type, canonical_label, attributes_json) VALUES (?, ?, ?, ?, ?)",
          params: ["node_bad_json", "lens_json", "concept", "Bad JSON Node", null]
        }
      ]
    });

    assert.equal(result.ok, false);
    assert.equal(result.error_type, "ontology_write_preflight");
    assert.match(JSON.stringify(result.preflight.errors), /null_required_column/);
    assert.match(result.hint, /attributes_json='\{\}'/);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_nodes WHERE node_id = 'node_bad_json'").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});
