import assert from "node:assert/strict";
import test from "node:test";

import { cleanupFixture, createFixture, createRepository } from "../support/ontology-agent-fixtures.js";

test("sql_batch_execute writes edit log, validates, and refreshes ontology embeddings", async () => {
  const fixture = createFixture();
  const repository = createRepository(fixture);
  try {
    const result = await repository.sqlBatchExecute({
      ontology_id: "lens_lazy",
      edit_summary: "Create lazy cook lens",
      statements: [
        {
          sql: "INSERT INTO ontology_lenses (ontology_id, name, description, status, intent_json) VALUES (?, ?, ?, ?, ?)",
          params: ["lens_lazy", "Lazy Cook", "Fast low-effort cooking lens", "ready", JSON.stringify({ perspective: "lazy cook" })]
        }
      ]
    });

    assert.equal(result.ok, true);
    assert.equal(result.validation.status, "pass");
    assert.equal(result.embedding.status, "ok");
    assert.equal(repository.getOntologyLens({ ontology_id: "lens_lazy" }).lens.embedding_status, "clean");
    assert.equal(repository.sqlQuery("SELECT COUNT(*) AS count FROM ontology_edit_log").rows[0].count, 1);
    assert.equal(repository.sqlQuery("SELECT dimensions FROM ontology_embedding_chunks WHERE ontology_id = 'lens_lazy'").rows[0].dimensions, 2);
  } finally {
    repository.close();
    cleanupFixture(fixture);
  }
});
