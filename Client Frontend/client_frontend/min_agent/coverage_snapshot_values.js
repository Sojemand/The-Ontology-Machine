import { normalizeRow, numberValue } from "./coverage_snapshot_context.js";

export function promotionCoverage(ctx, limit) {
  if (!ctx.hasTable("document_promotions") || !ctx.hasColumns("document_promotions", ["slot", "display_value"])) {
    return { available: false, promotion_count: 0, slot_count: 0, slots: [] };
  }
  const currentWhere = ctx.currentPromotionWhere();
  const optional = new Set(ctx.columns("document_promotions", ["slot_label", "value_type", "query_role", "candidate_id", "projection_id"]));
  const selectParts = [
    "slot",
    optional.has("slot_label") ? "slot_label" : "NULL AS slot_label",
    optional.has("value_type") ? "value_type" : "NULL AS value_type",
    optional.has("query_role") ? "query_role" : "NULL AS query_role",
    "COUNT(DISTINCT document_id) AS document_count",
    "COUNT(*) AS value_count",
    "COUNT(DISTINCT display_value) AS distinct_value_count",
    optional.has("candidate_id") ? "SUM(CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) AS candidate_backed_count" : "0 AS candidate_backed_count",
    optional.has("projection_id") ? "COUNT(DISTINCT NULLIF(projection_id, '')) AS projection_count" : "0 AS projection_count"
  ];
  const groupParts = ["slot", optional.has("slot_label") ? "slot_label" : null, optional.has("value_type") ? "value_type" : null, optional.has("query_role") ? "query_role" : null].filter(Boolean);
  const slots = ctx.database.prepare(`
    SELECT ${selectParts.join(", ")}
    FROM document_promotions
    ${currentWhere}
    GROUP BY ${groupParts.join(", ")}
    ORDER BY document_count DESC, value_count DESC, slot
    LIMIT ?
  `).all(limit).map((row) => normalizeRow(row));
  return {
    available: true,
    promotion_count: ctx.currentPromotionCount(),
    slot_count: ctx.currentPromotionSlotCount(),
    documents_with_promotions: ctx.currentPromotionDocumentCount(),
    slots
  };
}

export function fieldCoverage(ctx, limit) {
  if (!ctx.hasTable("extracted_fields") || !ctx.hasColumns("extracted_fields", ["key", "value"])) {
    return { available: false, extracted_field_count: 0, top_keys: [], empty_value_count: 0 };
  }
  const optional = new Set(ctx.columns("extracted_fields", ["value_type", "confidence", "source"]));
  const selectParts = [
    "key",
    optional.has("value_type") ? "value_type" : "NULL AS value_type",
    "COUNT(*) AS value_count",
    "COUNT(DISTINCT document_id) AS document_count",
    "COUNT(DISTINCT value) AS distinct_value_count",
    "SUM(CASE WHEN value IS NULL OR TRIM(value) = '' THEN 1 ELSE 0 END) AS empty_value_count"
  ];
  const groupParts = ["key", optional.has("value_type") ? "value_type" : null].filter(Boolean);
  const topKeys = ctx.database.prepare(`
    SELECT ${selectParts.join(", ")}
    FROM extracted_fields
    GROUP BY ${groupParts.join(", ")}
    ORDER BY document_count DESC, value_count DESC, key
    LIMIT ?
  `).all(limit).map((row) => normalizeRow(row));
  return {
    available: true,
    extracted_field_count: ctx.count("extracted_fields"),
    field_key_count: numberValue(ctx.database.prepare("SELECT COUNT(DISTINCT key) AS count FROM extracted_fields").get()?.count),
    empty_value_count: numberValue(ctx.database.prepare("SELECT COUNT(*) AS count FROM extracted_fields WHERE value IS NULL OR TRIM(value) = ''").get()?.count),
    top_keys: topKeys
  };
}
