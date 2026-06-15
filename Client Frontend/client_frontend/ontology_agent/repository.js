import { randomUUID } from "node:crypto";
import { DatabaseSync } from "node:sqlite";

import { createCoverageSnapshotRepository } from "../min_agent/coverage_snapshot.js";
import { createDocumentRepository } from "../min_agent/document_repository.js";
import { createImageRepository } from "../min_agent/image_repository.js";
import { createOntologyReadRepository } from "../min_agent/ontology_repository.js";
import { createProvenanceRepository } from "../min_agent/provenance_repository.js";
import { createQueryRepository } from "../min_agent/query_repository.js";
import { createSourceRepository } from "../min_agent/source_repository.js";
import { sanitizeRow } from "../min_agent/output_policy.js";
import { tableExists } from "../min_agent/corpus_tables.js";
import { assertOntologyWriteSql } from "./sql_write_policy.js";
import { refreshOntologyEmbeddings } from "./embedding_refresh.js";
import { validateOntologyPatchWithKernel } from "./kernel_validation.js";
import { preflightOntologyWriteBatch } from "./write_preflight.js";

function normalizeStatements(statements) {
  if (!Array.isArray(statements) || !statements.length) throw new Error("sql_batch_execute needs at least one statement.");
  if (statements.length > 50) throw new Error("sql_batch_execute accepts at most 50 statements per edit unit.");
  return statements.map((item) => ({
    sql: String(item?.sql || ""),
    params: Array.isArray(item?.params) ? item.params : []
  }));
}

function buildSqlBatchHint(error, statements) {
  const message = error instanceof Error ? error.message : "";
  const normalizedStatements = Array.isArray(statements) ? statements : [];
  const touchesLensStatus = normalizedStatements.some((statement) => /ontology_lenses/i.test(String(statement?.sql || ""))
    && (/status/i.test(String(statement?.sql || "")) || (Array.isArray(statement?.params) && statement.params.some((param) => String(param || "").toLowerCase() === "active"))));
  if (/check constraint failed/i.test(message) && touchesLensStatus) {
    return "ontology_lenses.status is a lifecycle field and accepts only draft, ready or archived. To activate a lens, set ontology_lenses.status = 'ready' and write ontology_activation with scope='corpus', scope_ref='self', is_active=1 and is_primary=1.";
  }
  if (/foreign key constraint failed/i.test(message)) {
    return "Foreign-key failure: write ontology rows parent-first. Insert or update ontology_lenses before rows that reference ontology_id; insert ontology_nodes before ontology_edges that reference them; insert ontology_runs before rows that reference run_id, or omit run_id; create evidence targets before ontology_evidence_links.";
  }
  return null;
}

function snapshotTable(database, tableName) {
  if (!tableExists(database, tableName)) return { count: 0, rows: [] };
  const count = Number(database.prepare(`SELECT COUNT(*) AS count FROM ${tableName}`).get()?.count) || 0;
  const rows = database.prepare(`SELECT * FROM ${tableName} ORDER BY rowid DESC LIMIT 20`).all().map(sanitizeRow);
  return { count, rows };
}

function affectedOntologyIds(database, tables) {
  const ids = new Set();
  for (const tableName of tables) {
    if (!tableName.startsWith("ontology_") || tableName === "ontology_embedding_chunks" || tableName === "ontology_edit_log") continue;
    if (!tableExists(database, tableName)) continue;
    if (tableName === "ontology_lenses") {
      for (const row of database.prepare("SELECT ontology_id FROM ontology_lenses WHERE embedding_status != 'clean' OR embedding_status IS NULL").all()) {
        if (row.ontology_id) ids.add(String(row.ontology_id));
      }
      continue;
    }
    for (const row of database.prepare(`SELECT DISTINCT ontology_id FROM ${tableName} WHERE ontology_id IS NOT NULL`).all()) {
      if (row.ontology_id) ids.add(String(row.ontology_id));
    }
  }
  return [...ids];
}

function markOntologyDirty(database, ontologyIds) {
  for (const ontologyId of ontologyIds) {
    database.prepare("UPDATE ontology_lenses SET embedding_status = 'dirty', updated_at = CURRENT_TIMESTAMP WHERE ontology_id = ?").run(ontologyId);
  }
}

export function createOntologyRepository({
  dbPath,
  dataDir,
  pipelineRoot = "",
  getRuntimeConfig,
  embedTextsFn,
  validatePatchFn = validateOntologyPatchWithKernel
}) {
  const database = new DatabaseSync(dbPath);
  database.exec("PRAGMA foreign_keys=ON");
  const imageRepository = createImageRepository({ database, dataDir });
  const queryRepository = createQueryRepository({ database });
  const sourceRepository = createSourceRepository({ database, imageRepository });
  const readRepository = createOntologyReadRepository({ database });

  async function sqlBatchExecute({ statements, edit_summary: editSummary = "", ontology_id: ontologyId = "" } = {}) {
    const editUnitId = `oeu_${randomUUID()}`;
    let tables = [];
    const affectedRows = {};
    let committed = false;
    try {
      const normalized = normalizeStatements(statements);
      const compiled = normalized.map((statement) => ({ ...assertOntologyWriteSql(statement.sql, statement.params), params: statement.params }));
      tables = [...new Set(compiled.map((statement) => statement.tableName))];
      const preflight = preflightOntologyWriteBatch({ database, statements: compiled, ontologyId });
      if (!preflight.ok) {
        return {
          ok: false,
          error: "ontology_write_preflight failed.",
          error_type: "ontology_write_preflight",
          repairable: Boolean(preflight.repairable),
          preflight,
          hint: preflight.hint,
          affected_tables: tables,
          affected_rows: affectedRows
        };
      }
      const before = Object.fromEntries(tables.map((tableName) => [tableName, snapshotTable(database, tableName)]));
      database.exec("BEGIN IMMEDIATE");
      for (const statement of compiled) {
        const result = database.prepare(statement.sql).run(...statement.params);
        affectedRows[statement.tableName] = (affectedRows[statement.tableName] || 0) + Number(result?.changes || 0);
      }
      const ontologyIds = ontologyId ? [String(ontologyId)] : affectedOntologyIds(database, tables);
      markOntologyDirty(database, ontologyIds);
      database.exec("COMMIT");
      committed = true;
      const after = Object.fromEntries(tables.map((tableName) => [tableName, snapshotTable(database, tableName)]));
      const validation = await validatePatchFn({ pipelineRoot, dbPath, ontologyId: ontologyId || "" });
      const embedding = validation.status === "fail"
        ? { status: "skipped", reason: "Validation failed; embeddings were not refreshed.", refreshed: [] }
        : await refreshOntologyEmbeddings({
            database,
            ontologyIds,
            runtimeConfig: typeof getRuntimeConfig === "function" ? getRuntimeConfig() : {},
            embedTextsFn
          });
      writeEditLog({ editUnitId, ontologyId, editSummary, tables, affectedRows, before, after, validation, embedding });
      return {
        ok: validation.status !== "fail",
        edit_unit_id: editUnitId,
        affected_tables: tables,
        affected_rows: affectedRows,
        validation,
        embedding
      };
    } catch (error) {
      if (!committed) {
        try {
          database.exec("ROLLBACK");
        } catch {
          // Rollback can fail if SQLite already closed the transaction.
        }
      }
      return {
        ok: false,
        error: error instanceof Error ? error.message : "sql_batch_execute failed.",
        hint: buildSqlBatchHint(error, statements),
        affected_tables: tables,
        affected_rows: affectedRows
      };
    }
  }

  function writeEditLog({ editUnitId, ontologyId, editSummary, tables, affectedRows, before, after, validation, embedding }) {
    if (!tableExists(database, "ontology_edit_log")) return;
    database.prepare(
      "INSERT INTO ontology_edit_log (edit_id, edit_unit_id, ontology_id, tool_name, sql_summary, affected_tables_json, affected_rows_json, before_rows_json, after_rows_json, verification_status, verification_report_json, created_at) "
      + "VALUES (?, ?, ?, 'sql_batch_execute', ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)"
    ).run(
      `oel_${randomUUID()}`,
      editUnitId,
      ontologyId || null,
      editSummary || "Ontology Agent SQL batch",
      JSON.stringify(tables),
      JSON.stringify(affectedRows),
      JSON.stringify(before),
      JSON.stringify(after),
      validation?.status || null,
      JSON.stringify({ validation, embedding })
    );
  }

  return {
    ...queryRepository,
    ...createCoverageSnapshotRepository({ database }),
    ...readRepository,
    ...sourceRepository,
    ...createDocumentRepository({ database, buildSource: sourceRepository.buildSource, imageRepository }),
    ...createProvenanceRepository({ database, buildSource: sourceRepository.buildSource }),
    resolveImage(docId, page = 1) {
      return imageRepository.resolveImage(docId, page);
    },
    sqlBatchExecute,
    close() {
      database.close();
    }
  };
}
