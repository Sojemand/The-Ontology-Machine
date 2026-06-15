import { classificationCoverage } from "./coverage_snapshot_classification.js";
import {
  containsLimitSizedList,
  createCoverageContext,
  normalizeFocus,
  normalizeLimit
} from "./coverage_snapshot_context.js";
import {
  availabilitySummary,
  databaseSummary,
  materializationSummary
} from "./coverage_snapshot_database.js";
import { rowCoverage, weakSpots } from "./coverage_snapshot_rows.js";
import { fieldCoverage, promotionCoverage } from "./coverage_snapshot_values.js";

export function createCoverageSnapshotRepository({ database }) {
  const ctx = createCoverageContext(database);

  function databaseCoverageSnapshot(input = {}) {
    const focus = normalizeFocus(input?.focus);
    const limit = normalizeLimit(input?.limit);
    const activeWhere = ctx.activeDocumentWhere();
    const snapshot = {
      ok: true,
      schema_version: "client_frontend.database_coverage_snapshot.v1",
      focus,
      database: databaseSummary(ctx, activeWhere),
      materialization: materializationSummary(ctx, limit),
      availability: availabilitySummary(ctx),
      limits: { limit, truncated: false }
    };
    if (focus === "overview" || focus === "release") {
      snapshot.classification_coverage = classificationCoverage(ctx, activeWhere, limit);
    }
    if (focus === "overview" || focus === "promotions") {
      snapshot.promotion_coverage = promotionCoverage(ctx, limit);
    }
    if (focus === "overview" || focus === "fields") {
      snapshot.field_coverage = fieldCoverage(ctx, limit);
    }
    if (focus === "overview" || focus === "rows") {
      snapshot.row_coverage = rowCoverage(ctx, limit);
    }
    if (focus === "overview" || focus === "weak_spots") {
      snapshot.weak_spots = weakSpots(ctx, activeWhere, limit);
    }
    snapshot.limits.truncated = containsLimitSizedList(snapshot, limit);
    return snapshot;
  }

  return { databaseCoverageSnapshot };
}
