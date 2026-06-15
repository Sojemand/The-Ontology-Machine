import assert from "node:assert/strict";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { cleanupFixture, createFixture, createRepository } from "../support/ontology-agent-fixtures.js";

test("sql_batch_execute rejects null required identifier values before transaction", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_null_id",
      edit_summary: "Bad term id",
      statements: [
        {
          sql: "INSERT INTO ontology_terms (term_id, ontology_id, label, normalized_label, term_kind) VALUES (?, ?, ?, ?, ?)",
          params: [null, "lens_null_id", "Story Arc", "story_arc", "framework"]
        }
      ]
    });

    assert.equal(result.ok, false);
    assert.match(result.error, /non-empty value for term_id/);
    assert.deepEqual(result.affected_tables, []);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_terms").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("embedding refresh reports missing ontology object ids without partial chunk writes", async () => {
  const fixture = createFixture();
  {
    const database = new DatabaseSync(fixture.dbPath);
    database.prepare("INSERT INTO ontology_lenses (ontology_id, name, status) VALUES (?, ?, ?)").run("lens_bad_ids", "Bad IDs", "ready");
    database.prepare("INSERT INTO ontology_nodes (ontology_id, node_type, canonical_label) VALUES (?, ?, ?)").run("lens_bad_ids", "concept", "Missing Node ID");
    database.close();
  }
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_bad_ids",
      edit_summary: "Trigger embedding refresh for bad existing object",
      statements: [
        {
          sql: "UPDATE ontology_lenses SET description = ? WHERE ontology_id = ?",
          params: ["Trigger refresh", "lens_bad_ids"]
        }
      ]
    });

    assert.equal(result.ok, true);
    assert.equal(result.embedding.status, "warning");
    assert.match(result.embedding.refreshed[0].error, /missing stable IDs/);
    assert.equal(repository.sqlQuery("SELECT embedding_status FROM ontology_lenses WHERE ontology_id = 'lens_bad_ids'").rows[0].embedding_status, "unavailable");
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_embedding_chunks WHERE ontology_id = 'lens_bad_ids'").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute can create a ready active primary lens with activation row", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_primary",
      edit_summary: "Create active primary lens",
      statements: [
        {
          sql: "UPDATE ontology_activation SET is_primary = 0 WHERE scope = ? AND scope_ref = ? AND is_active = 1 AND is_primary = 1",
          params: ["corpus", "self"]
        },
        {
          sql: "INSERT INTO ontology_lenses (ontology_id, name, status, intent_json) VALUES (?, ?, ?, ?)",
          params: ["lens_primary", "Primary Lens", "ready", JSON.stringify({ goal: "primary test lens" })]
        },
        {
          sql: "INSERT INTO ontology_activation (ontology_id, scope, scope_ref, is_active, is_primary, priority) VALUES (?, ?, ?, ?, ?, ?)",
          params: ["lens_primary", "corpus", "self", 1, 1, 0]
        }
      ]
    });

    assert.equal(result.ok, true);
    assert.equal(repository.sqlQuery("SELECT status FROM ontology_lenses WHERE ontology_id = 'lens_primary'").rows[0].status, "ready");
    assert.deepEqual(
      repository.sqlQuery("SELECT scope, scope_ref, is_active, is_primary FROM ontology_activation WHERE ontology_id = 'lens_primary'").rows[0],
      { scope: "corpus", scope_ref: "self", is_active: 1, is_primary: 1 }
    );
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});
