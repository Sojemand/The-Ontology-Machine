import { cosineSimilarity, toFloat32Array } from "../vector.js";
import { clipText } from "./output_policy.js";
import { getAvailableColumns, tableExists } from "./corpus_tables.js";
import { createKeywordSearch } from "./keyword_search.js";
import { promotionSqlExpressions } from "./promotion_surface.js";
import { buildSchemaSummary, buildSqlErrorResult } from "./schema_summary.js";
import { assertReadOnlySql, collectCappedRows } from "./sql_policy.js";
import { MAX_SQL_ROWS } from "./types.js";

export { assertReadOnlySql } from "./sql_policy.js";
export { buildSchemaSummary, buildSqlErrorResult } from "./schema_summary.js";

export function createQueryRepository({ database }) {
  const schemaSummary = buildSchemaSummary(database);
  const keywordColumns = getAvailableColumns(database, "documents", [
    "id",
    "file_name",
    "file_path",
    "document_type",
    "category",
    "subcategory",
    "content_hash",
    "page_count",
    "content_free_text",
    "content_fields_json",
    "content_rows_json"
  ]);
  const keywordSearch = createKeywordSearch({ database, keywordColumns });
  const promotionSql = promotionSqlExpressions(database, "d");

  function countRows(tableName) {
    return tableExists(database, tableName) ? Number(database.prepare(`SELECT COUNT(*) AS count FROM ${tableName}`).get()?.count) || 0 : 0;
  }

  function semanticIndexState() {
    const chunkCount = countRows("embedding_chunks");
    const documentCount = countRows("embeddings");
    return {
      available: chunkCount > 0 || documentCount > 0,
      chunk_count: chunkCount,
      document_embedding_count: documentCount,
      error: chunkCount > 0 || documentCount > 0 ? null : "No embeddings available in the corpus. Use SQL/documents_fts or the lexical fallback results."
    };
  }

  function semanticSearch(queryVector, limit = 5) {
    const state = semanticIndexState();
    if (!state.available) return { available: false, error: state.error, results: [] };
    const normalizedLimit = Math.min(20, Math.max(1, Number(limit) || 5));
    const bestByDocument = new Map();
    const useChunks = state.chunk_count > 0;
    const statement = useChunks
      ? database.prepare(`SELECT d.id, d.file_name, d.file_path, d.content_hash, d.page_count, d.content_free_text, ${promotionSql.title} AS promotion_title, ${promotionSql.date} AS promotion_date, ${promotionSql.summary} AS promotion_summary, ec.vector, ec.dimensions, ec.chunk_text AS embedding_text, ec.page AS chunk_page, ec.chunk_type FROM embedding_chunks ec JOIN documents d ON d.id = ec.document_id`)
      : database.prepare(`SELECT d.id, d.file_name, d.file_path, d.content_hash, d.page_count, d.content_free_text, ${promotionSql.title} AS promotion_title, ${promotionSql.date} AS promotion_date, ${promotionSql.summary} AS promotion_summary, e.vector, e.dimensions, e.embedding_text, NULL AS chunk_page, NULL AS chunk_type FROM embeddings e JOIN documents d ON d.id = e.document_id`);
    for (const row of statement.iterate()) {
      const score = cosineSimilarity(queryVector, toFloat32Array(row.vector, row.dimensions));
      const current = bestByDocument.get(row.id);
      if (!current || score > current.score) bestByDocument.set(row.id, { row, score });
    }
    return buildSemanticSearchResult(bestByDocument, normalizedLimit, useChunks);
  }

  return {
    schemaSummary,
    sqlQuery(query, runtimePolicy = null) {
      return collectCappedRows(database.prepare(assertReadOnlySql(query)), [], runtimePolicy?.max_sql_rows || MAX_SQL_ROWS);
    },
    countDocuments() {
      return Number(database.prepare("SELECT COUNT(*) AS count FROM documents").get()?.count) || 0;
    },
    semanticIndexState,
    keywordSearch,
    semanticSearch
  };
}

function buildSemanticSearchResult(bestByDocument, normalizedLimit, useChunks) {
  const topResults = Array.from(bestByDocument.values()).sort((left, right) => right.score - left.score).slice(0, normalizedLimit);
  return {
    available: true,
    mode: useChunks ? "semantic_chunks" : "semantic_documents",
    result_count: topResults.length,
    results: topResults.map(({ row, score }) => ({
      id: row.id,
      file_name: row.file_name,
      file_path: row.file_path,
      date: row.promotion_date || null,
      title: row.promotion_title || row.file_name,
      score: Number(score.toFixed(6)),
      page: row.chunk_page || null,
      chunk_type: row.chunk_type || null,
      snippet: clipText(row.embedding_text || row.promotion_summary || row.content_free_text || "", 400)
    }))
  };
}
