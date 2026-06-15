import assert from "node:assert/strict";
import test from "node:test";

import { cleanupFixture, createFixture, createRepository } from "../support/ontology-agent-fixtures.js";

test("sql_batch_execute rejects non-allowlisted writes before opening the transaction", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      edit_summary: "Bad write",
      statements: [{ sql: "UPDATE documents SET file_name = ? WHERE id = ?", params: ["bad.pdf", "doc-1"] }]
    });

    assert.equal(result.ok, false);
    assert.match(result.error, /cannot write table 'documents'/);
    assert.equal(repository.sqlQuery("SELECT file_name FROM documents WHERE id = 'doc-1'").rows[0].file_name, "alpha.pdf");
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_edit_log").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute rolls back the full batch when a later statement fails", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      edit_summary: "Partial failure",
      statements: [
        { sql: "INSERT INTO ontology_lenses (ontology_id, name) VALUES (?, ?)", params: ["lens_bad", "Bad Lens"] },
        { sql: "INSERT INTO ontology_lenses (ontology_id, name) VALUES (?, ?)", params: ["lens_bad", "Duplicate Lens"] }
      ]
    });

    assert.equal(result.ok, false);
    assert.match(result.error, /UNIQUE constraint failed/);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_lenses WHERE ontology_id = 'lens_bad'").rows[0].count, 0);
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_edit_log").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});

test("sql_batch_execute returns validation failure and skips embedding refresh", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture, {
    validatePatchFn: async () => ({ status: "fail", checks: [], warnings: [], errors: [{ code: "broken", message: "Graph broken" }] })
  });
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_fail",
      edit_summary: "Create failing lens",
      statements: [{ sql: "INSERT INTO ontology_lenses (ontology_id, name) VALUES (?, ?)", params: ["lens_fail", "Fail Lens"] }]
    });

    assert.equal(result.ok, false);
    assert.equal(result.validation.status, "fail");
    assert.equal(result.embedding.status, "skipped");
    assert.equal(repository.sqlQuery("SELECT verification_status FROM ontology_edit_log").rows[0].verification_status, "fail");
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_embedding_chunks WHERE ontology_id = 'lens_fail'").rows[0].count, 0);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});
