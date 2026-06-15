import { normalizeRow, numberValue } from "./coverage_snapshot_context.js";

export function databaseSummary(ctx, activeWhere) {
  return {
    document_count: ctx.count("documents", activeWhere),
    archived_document_count: ctx.hasColumns("documents", ["is_archived"]) ? ctx.count("documents", " WHERE COALESCE(is_archived, 0) = 1") : 0,
    page_count_total: pageCountTotal(ctx),
    page_count_basis: pageCountBasis(ctx),
    payloads: {
      structured: payloadCount(ctx, "structured_json"),
      normalized: payloadCount(ctx, "normalized_json"),
      projection: payloadCount(ctx, "projection_json")
    },
    embeddings: {
      available: ctx.count("embedding_chunks") > 0 || ctx.count("embeddings") > 0,
      chunk_count: ctx.count("embedding_chunks"),
      document_embedding_count: ctx.count("embeddings")
    },
    evidence: {
      evidence_atoms: ctx.count("evidence_atoms"),
      slot_candidates: ctx.count("slot_candidates"),
      current_promotions: ctx.currentPromotionCount(),
      promotion_slots: ctx.currentPromotionSlotCount()
    }
  };
}

export function materializationSummary(ctx, limit) {
  const installationColumns = ctx.columns("installation_state", [
    "active_release_id",
    "active_release_version",
    "active_release_fingerprint",
    "active_snapshot_id",
    "master_taxonomy_id",
    "master_taxonomy_version",
    "runtime_locale",
    "integrity_status",
    "materialization_version"
  ]);
  const installationSelector = ctx.hasColumns("installation_state", ["singleton"]) ? " WHERE singleton = 1" : " LIMIT 1";
  const installation = installationColumns.length
    ? normalizeRow(ctx.database.prepare(`SELECT ${installationColumns.join(", ")} FROM installation_state${installationSelector}`).get() || {})
    : {};
  const payloadFingerprints = releaseFingerprintGroups(ctx, "document_payloads", limit);
  const promotionFingerprints = releaseFingerprintGroups(ctx, "document_promotions", limit, ctx.currentPromotionWhere());
  const processingStates = ctx.grouped("document_processing_state", ["materialization_state"], { limit });
  const projections = ctx.grouped(
    "document_processing_state",
    ["projection_id"],
    { where: "WHERE projection_id IS NOT NULL AND projection_id != ''", orderBy: "row_count DESC, projection_id", limit }
  );
  const distinctFingerprints = new Set([
    ...payloadFingerprints.map((row) => row.release_fingerprint).filter(Boolean),
    ...promotionFingerprints.map((row) => row.release_fingerprint).filter(Boolean)
  ]);
  return {
    active_release_id: installation.active_release_id || null,
    active_release_version: installation.active_release_version || null,
    active_release_fingerprint: installation.active_release_fingerprint || null,
    active_snapshot_id: installation.active_snapshot_id || null,
    master_taxonomy_id: installation.master_taxonomy_id || null,
    master_taxonomy_version: installation.master_taxonomy_version || null,
    runtime_locale: installation.runtime_locale || null,
    integrity_status: installation.integrity_status || null,
    materialization_version: installation.materialization_version || null,
    payload_release_fingerprints: payloadFingerprints,
    promotion_release_fingerprints: promotionFingerprints,
    mixed_release_materialization: distinctFingerprints.size > 1,
    processing_states: processingStates,
    projections
  };
}

export function availabilitySummary(ctx) {
  return Object.fromEntries([
    "documents",
    "document_payloads",
    "document_promotions",
    "extracted_fields",
    "extracted_rows",
    "slot_candidates",
    "evidence_atoms",
    "installation_state",
    "semantic_snapshots",
    "document_processing_state",
    "embedding_chunks",
    "embeddings",
    "materialization_audit"
  ].map((tableName) => [tableName, ctx.hasTable(tableName)]));
}

function payloadCount(ctx, columnName) {
  if (!ctx.hasColumns("document_payloads", [columnName])) return 0;
  return numberValue(ctx.database.prepare(`SELECT COUNT(*) AS count FROM document_payloads WHERE ${columnName} IS NOT NULL AND ${columnName} != ''`).get()?.count);
}

function pageCountBasis(ctx) {
  if (ctx.hasColumns("source_document_pages", ["document_id"])) return "source_document_pages";
  if (ctx.hasColumns("structural_units", ["unit_type"])) return "structural_units.page_unit";
  if (ctx.hasColumns("documents", ["page_count"])) return "documents.page_count_legacy_sum";
  return "documents.count";
}

function pageCountTotal(ctx) {
  if (ctx.hasColumns("source_document_pages", ["document_id"])) {
    if (ctx.hasColumns("documents", ["id"])) {
      return numberValue(ctx.database.prepare(
        "SELECT COUNT(*) AS count FROM source_document_pages sdp JOIN documents d ON d.id = sdp.document_id"
        + ctx.activeDocumentWhere("d")
      ).get()?.count);
    }
    return ctx.count("source_document_pages");
  }
  if (ctx.hasColumns("structural_units", ["unit_type"])) {
    const activeWhere = ctx.hasColumns("structural_units", ["document_id"]) && ctx.hasColumns("documents", ["id"])
      ? ctx.activeDocumentWhere("d")
      : "";
    const joinSql = activeWhere ? " LEFT JOIN documents d ON d.id = unit.document_id" : "";
    const whereSql = activeWhere ? `${activeWhere} AND unit.unit_type = 'page_unit'` : " WHERE unit.unit_type = 'page_unit'";
    return numberValue(ctx.database.prepare(`SELECT COUNT(*) AS count FROM structural_units unit${joinSql}${whereSql}`).get()?.count);
  }
  if (ctx.hasColumns("documents", ["page_count"])) {
    return ctx.countWhereColumns("documents", {
      columns: ["page_count"],
      sql: () => `SELECT SUM(COALESCE(page_count, 1)) AS count FROM documents${ctx.activeDocumentWhere()}`
    });
  }
  return ctx.count("documents", ctx.activeDocumentWhere());
}

function releaseFingerprintGroups(ctx, tableName, limit, where = "") {
  if (!ctx.hasColumns(tableName, ["release_fingerprint"])) return [];
  const wherePrefix = where ? `${where} AND` : "WHERE";
  return ctx.database.prepare(`
    SELECT release_fingerprint, COUNT(*) AS row_count
    FROM ${tableName}
    ${wherePrefix} release_fingerprint IS NOT NULL AND release_fingerprint != ''
    GROUP BY release_fingerprint
    ORDER BY row_count DESC, release_fingerprint
    LIMIT ?
  `).all(limit).map((row) => normalizeRow(row));
}
