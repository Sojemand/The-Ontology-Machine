import { MAX_EVIDENCE_COUNT, MAX_FIELD_COUNT, MAX_ROW_COUNT, MAX_TEXT_LENGTH } from "./types.js";
import { sanitizeRow } from "./output_policy.js";
import { getAvailableColumns, getOptionalRow, listOptionalRows } from "./corpus_tables.js";

const VIEW_LIMITS = {
  full: { payload: { normalized: 3_000, structured: 3_000, projection: 2_000 } },
  summary: { fields: 12, rows: 2, evidence: 4, text: 900, payload: { normalized: 800, structured: 800, projection: 600 } },
  ontology_evidence: { fields: 40, rows: 8, evidence: 16, text: 1_800, payload: { normalized: 1_800, structured: 1_800, projection: 1_200 } },
  rows: { fields: 12, rows: 40, evidence: 8, text: 700, payload: { normalized: 700, structured: 1_200, projection: 500 } },
  provenance: { fields: 80, rows: 8, evidence: 30, text: 1_500, payload: { normalized: 2_000, structured: 2_000, projection: 1_000 } }
};

function clampLimit(value, fallback, hardMax) {
  const parsed = Number(value);
  const selected = Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
  return Math.max(0, Math.min(selected, hardMax));
}

function selectColumns(database, table, candidates) {
  return getAvailableColumns(database, table, candidates);
}

export function normalizeDocumentViewName(viewName) {
  return VIEW_LIMITS[viewName] ? viewName : "full";
}

export function resolveDocumentViewLimits(runtimePolicy, viewName) {
  const hardLimits = {
    evidence: runtimePolicy?.max_evidence_count || MAX_EVIDENCE_COUNT,
    fields: runtimePolicy?.max_field_count || MAX_FIELD_COUNT,
    rows: runtimePolicy?.max_row_count || MAX_ROW_COUNT,
    text: runtimePolicy?.max_text_length || MAX_TEXT_LENGTH
  };
  const viewLimits = VIEW_LIMITS[normalizeDocumentViewName(viewName)];
  return {
    evidence: clampLimit(viewLimits.evidence, hardLimits.evidence, hardLimits.evidence),
    fields: clampLimit(viewLimits.fields, hardLimits.fields, hardLimits.fields),
    rows: clampLimit(viewLimits.rows, hardLimits.rows, hardLimits.rows),
    text: clampLimit(viewLimits.text, hardLimits.text, hardLimits.text),
    payload: viewLimits.payload || VIEW_LIMITS.full.payload
  };
}

export function sourceDocumentContext(database, docId) {
  const pageColumns = selectColumns(database, "source_document_pages", [
    "source_document_id",
    "document_id",
    "page_index",
    "page_label",
    "prev_document_id",
    "next_document_id",
    "confidence"
  ]);
  if (!pageColumns.includes("source_document_id") || !pageColumns.includes("document_id")) {
    return { available: false, page: null, source_document: null, classifications: [] };
  }
  const page = getOptionalRow(
    database,
    "source_document_pages",
    `SELECT ${pageColumns.join(", ")} FROM source_document_pages WHERE document_id = ? LIMIT 1`,
    [docId]
  );
  const sourceDocumentId = page?.source_document_id ? String(page.source_document_id) : "";
  if (!sourceDocumentId) {
    return { available: true, page: null, source_document: null, classifications: [] };
  }
  const sourceColumns = selectColumns(database, "source_documents", [
    "source_document_id",
    "source_uri",
    "source_file_id",
    "source_artifact_id",
    "ingest_run_id",
    "source_title",
    "source_kind",
    "page_count",
    "first_document_id",
    "last_document_id",
    "source_content_hash",
    "metadata_json"
  ]);
  const sourceDocument = sourceColumns.includes("source_document_id")
    ? getOptionalRow(
        database,
        "source_documents",
        `SELECT ${sourceColumns.join(", ")} FROM source_documents WHERE source_document_id = ? LIMIT 1`,
        [sourceDocumentId]
      )
    : null;
  const classificationColumns = selectColumns(database, "source_document_classifications", [
    "source_document_id",
    "classification_scope",
    "ontology_id",
    "document_type",
    "category",
    "subcategory",
    "confidence",
    "status",
    "basis_json",
    "created_by"
  ]);
  const classifications = classificationColumns.includes("source_document_id")
    ? listOptionalRows(
        database,
        "source_document_classifications",
        `SELECT ${classificationColumns.join(", ")} FROM source_document_classifications WHERE source_document_id = ? ORDER BY classification_scope, COALESCE(ontology_id, '')`,
        [sourceDocumentId]
      ).map(sanitizeRow)
    : [];
  return {
    available: true,
    page: sanitizeRow(page),
    source_document: sourceDocument ? sanitizeRow(sourceDocument) : null,
    classifications
  };
}

export function structuralUnits(database, docId, sourceDocumentId, limit) {
  const columns = selectColumns(database, "structural_units", [
    "unit_id",
    "source_document_id",
    "unit_type",
    "parent_unit_id",
    "document_id",
    "page_index",
    "page_label",
    "ordinal",
    "start_page_index",
    "end_page_index",
    "label",
    "unit_origin",
    "confidence",
    "status"
  ]);
  if (!columns.includes("unit_id")) return [];
  if (columns.includes("document_id")) {
    const rows = listOptionalRows(
      database,
      "structural_units",
      `SELECT ${columns.join(", ")} FROM structural_units WHERE document_id = ? ORDER BY ordinal, unit_type, unit_id LIMIT ?`,
      [docId, limit]
    ).map(sanitizeRow);
    if (rows.length || !sourceDocumentId || !columns.includes("source_document_id")) return rows;
  }
  if (!sourceDocumentId || !columns.includes("source_document_id")) return [];
  return listOptionalRows(
    database,
    "structural_units",
    `SELECT ${columns.join(", ")} FROM structural_units WHERE source_document_id = ? ORDER BY ordinal, unit_type, unit_id LIMIT ?`,
    [sourceDocumentId, limit]
  ).map(sanitizeRow);
}
