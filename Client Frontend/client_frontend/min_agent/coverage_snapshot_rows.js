import { normalizeDocumentRow, normalizeRow, rankedCounts } from "./coverage_snapshot_context.js";
import { genericClassificationCount, reviewSignals } from "./coverage_snapshot_classification.js";

export function rowCoverage(ctx, limit) {
  if (!ctx.hasTable("extracted_rows") || !ctx.hasColumns("extracted_rows", ["row_json"])) {
    return { available: false, extracted_row_count: 0, row_types: [], top_cell_keys: [] };
  }
  return {
    available: true,
    extracted_row_count: ctx.count("extracted_rows"),
    row_types: rowTypes(ctx, limit),
    top_cell_keys: rowCellKeys(ctx, limit)
  };
}

export function weakSpots(ctx, activeWhere, limit) {
  return {
    generic_or_other_classification_count: genericClassificationCount(ctx, activeWhere),
    review_signals: reviewSignals(ctx, activeWhere),
    unbacked_slot_candidates: unbackedSlotCandidates(ctx, limit),
    documents_with_low_promotions: documentsWithLowPromotions(ctx, limit),
    materialization_audits: materializationAudits(ctx, limit)
  };
}

function rowTypes(ctx, limit) {
  try {
    return ctx.database.prepare(`
      SELECT COALESCE(NULLIF(json_extract(row_json, '$._row_type'), ''), 'unknown') AS row_type, COUNT(*) AS row_count
      FROM extracted_rows
      GROUP BY row_type
      ORDER BY row_count DESC, row_type
      LIMIT ?
    `).all(limit).map((row) => normalizeRow(row));
  } catch {
    return parsedRowStats(ctx, limit).row_types;
  }
}

function rowCellKeys(ctx, limit) {
  try {
    return ctx.database.prepare(`
      SELECT key AS cell_key, COUNT(*) AS row_count
      FROM extracted_rows, json_each(row_json)
      WHERE key NOT LIKE '\\_%' ESCAPE '\\'
      GROUP BY key
      ORDER BY row_count DESC, key
      LIMIT ?
    `).all(limit).map((row) => normalizeRow(row));
  } catch {
    return parsedRowStats(ctx, limit).top_cell_keys;
  }
}

function parsedRowStats(ctx, limit) {
  const rows = ctx.database.prepare("SELECT row_json FROM extracted_rows").all();
  const typeCounts = new Map();
  const keyCounts = new Map();
  for (const row of rows) {
    let parsed = null;
    try {
      parsed = JSON.parse(String(row.row_json || "{}"));
    } catch {
      parsed = null;
    }
    const rowType = String(parsed?._row_type || "unknown");
    typeCounts.set(rowType, (typeCounts.get(rowType) || 0) + 1);
    if (parsed && typeof parsed === "object") {
      for (const key of Object.keys(parsed)) {
        if (!key.startsWith("_")) keyCounts.set(key, (keyCounts.get(key) || 0) + 1);
      }
    }
  }
  return {
    row_types: rankedCounts(typeCounts, "row_type", limit),
    top_cell_keys: rankedCounts(keyCounts, "cell_key", limit)
  };
}

function unbackedSlotCandidates(ctx, limit) {
  if (!ctx.hasTable("slot_candidates") || !ctx.hasColumns("slot_candidates", ["slot", "is_projection_backed"])) return [];
  return ctx.database.prepare(`
    SELECT slot, COUNT(*) AS candidate_count, COUNT(DISTINCT document_id) AS document_count
    FROM slot_candidates
    WHERE COALESCE(is_projection_backed, 0) = 0
    GROUP BY slot
    ORDER BY candidate_count DESC, slot
    LIMIT ?
  `).all(limit).map((row) => normalizeRow(row));
}

function documentsWithLowPromotions(ctx, limit) {
  if (!ctx.hasTable("documents")) return [];
  const documentColumns = ctx.columns("documents", ["id", "file_name", "document_type", "category", "subcategory"]);
  if (!documentColumns.includes("id")) return [];
  const activeWhere = ctx.activeDocumentWhere();
  const selectedColumns = [
    "d.id",
    documentColumns.includes("file_name") ? "d.file_name" : "NULL AS file_name",
    documentColumns.includes("document_type") ? "d.document_type" : "NULL AS document_type",
    documentColumns.includes("category") ? "d.category" : "NULL AS category",
    documentColumns.includes("subcategory") ? "d.subcategory" : "NULL AS subcategory",
    ctx.hasColumns("document_promotions", ["document_id"]) ? "COUNT(p.document_id) AS promotion_count" : "0 AS promotion_count"
  ];
  if (!ctx.hasColumns("document_promotions", ["document_id"])) {
    return ctx.database.prepare(`
      SELECT ${selectedColumns.join(", ")}
      FROM documents d
      ${activeWhere ? activeWhere.replace(/^ WHERE /i, "WHERE ") : ""}
      ORDER BY d.id
      LIMIT ?
    `).all(limit).map((row) => normalizeDocumentRow(row));
  }
  const currentWhere = ctx.currentPromotionWhere("p");
  return ctx.database.prepare(`
    SELECT ${selectedColumns.join(", ")}
    FROM documents d
    LEFT JOIN document_promotions p ON p.document_id = d.id ${currentWhere ? `AND ${currentWhere.replace(/^WHERE\s+/i, "")}` : ""}
    ${activeWhere ? activeWhere.replace(/^ WHERE /i, "WHERE ") : ""}
    GROUP BY d.id
    HAVING promotion_count < 2
    ORDER BY promotion_count ASC, d.id
    LIMIT ?
  `).all(limit).map((row) => normalizeDocumentRow(row));
}

function materializationAudits(ctx, limit) {
  if (!ctx.hasTable("materialization_audit") || !ctx.hasColumns("materialization_audit", ["level", "code"])) return [];
  return ctx.database.prepare(`
    SELECT level, code, COUNT(*) AS row_count
    FROM materialization_audit
    GROUP BY level, code
    ORDER BY row_count DESC, level, code
    LIMIT ?
  `).all(limit).map((row) => normalizeRow(row));
}
