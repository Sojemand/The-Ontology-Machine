import assert from "node:assert/strict";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { assertReadOnlySql, buildSchemaSummary, trimHistoryForContext } from "../../server/min_agent.js";

test("assertReadOnlySql accepts single read-only statements", () => {
  assert.equal(assertReadOnlySql("SELECT * FROM documents;"), "SELECT * FROM documents");
  assert.equal(assertReadOnlySql("WITH x AS (SELECT 1) SELECT * FROM x"), "WITH x AS (SELECT 1) SELECT * FROM x");
});

test("assertReadOnlySql rejects mutating statements", () => {
  assert.throws(() => assertReadOnlySql("DELETE FROM documents"), /Only SELECT or WITH queries|disallowed SQL/i);
  assert.throws(() => assertReadOnlySql("SELECT 1; DROP TABLE documents"), /Multiple SQL statements/i);
});

test("buildSchemaSummary lists user tables and columns", () => {
  const database = new DatabaseSync(":memory:");
  database.exec(`
    CREATE TABLE documents (id TEXT, file_name TEXT, file_path TEXT);
    CREATE TABLE extracted_fields (document_id TEXT, key TEXT, value TEXT);
  `);

  const summary = buildSchemaSummary(database);
  assert.match(summary, /Layer guide:/);
  assert.match(summary, /documents: primary normalized-first document metadata layer/i);
  assert.match(summary, /documents\(id, file_name, file_path\)/);
  assert.match(summary, /extracted_fields\(document_id, key, value\)/);

  database.close();
});

test("trimHistoryForContext preserves markdown line breaks for later turns", () => {
  const trimmed = trimHistoryForContext(
    [{ role: "assistant", content: "## Analyse\n\n| Feld | Wert |\n|---|---|\n| alpha | beta |" }],
    60_096
  );

  assert.equal(trimmed.length, 1);
  assert.match(trimmed[0].content, /\n\| Feld \| Wert \|\n\|---\|---\|\n\| alpha \| beta \|/);
});
