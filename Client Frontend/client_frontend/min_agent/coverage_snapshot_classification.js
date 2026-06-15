import { GENERIC_VALUES, numberValue } from "./coverage_snapshot_context.js";

export function classificationCoverage(ctx, activeWhere, limit) {
  return {
    document_types: ctx.grouped("documents", ["document_type"], { where: activeWhere, orderBy: "row_count DESC, document_type", limit }),
    categories: ctx.grouped("documents", ["category"], { where: activeWhere, orderBy: "row_count DESC, category", limit }),
    subcategories: ctx.grouped("documents", ["subcategory"], { where: activeWhere, orderBy: "row_count DESC, subcategory", limit }),
    generic_or_other_documents: genericClassificationCount(ctx, activeWhere),
    review_signals: reviewSignals(ctx, activeWhere)
  };
}

export function genericClassificationCount(ctx, activeWhere) {
  if (!ctx.hasTable("documents")) return 0;
  const available = ctx.columns("documents", ["document_type", "category", "subcategory"]);
  if (!available.length) return 0;
  const genericParams = Array.from(GENERIC_VALUES);
  const expression = available
    .map((column) => `LOWER(COALESCE(${column}, '')) IN (${genericParams.map(() => "?").join(", ")})`)
    .join(" OR ");
  const where = activeWhere ? `${activeWhere} AND (${expression})` : ` WHERE ${expression}`;
  const params = available.flatMap(() => genericParams);
  return numberValue(ctx.database.prepare(`SELECT COUNT(*) AS count FROM documents${where}`).get(...params)?.count);
}

export function reviewSignals(ctx, activeWhere) {
  if (!ctx.hasTable("documents")) {
    return { documents_with_review: 0, interpreter_review: 0, normalizer_review: 0, validator_issues: 0 };
  }
  const available = new Set(ctx.columns("documents", [
    "needs_review",
    "interpreter_needs_review",
    "normalizer_needs_review",
    "validator_issues_count"
  ]));
  const countFlag = (column) => available.has(column)
    ? numberValue(ctx.database.prepare(`SELECT COUNT(*) AS count FROM documents${activeWhere}${activeWhere ? " AND" : " WHERE"} COALESCE(${column}, 0) ${column === "validator_issues_count" ? ">" : "="} ${column === "validator_issues_count" ? "0" : "1"}`).get()?.count)
    : 0;
  const flagExpressions = ["needs_review", "interpreter_needs_review", "normalizer_needs_review"]
    .filter((column) => available.has(column))
    .map((column) => `COALESCE(${column}, 0) = 1`);
  if (available.has("validator_issues_count")) flagExpressions.push("COALESCE(validator_issues_count, 0) > 0");
  const documentsWithReview = flagExpressions.length
    ? numberValue(ctx.database.prepare(`SELECT COUNT(*) AS count FROM documents${activeWhere}${activeWhere ? " AND" : " WHERE"} (${flagExpressions.join(" OR ")})`).get()?.count)
    : 0;
  return {
    documents_with_review: documentsWithReview,
    interpreter_review: countFlag("interpreter_needs_review"),
    normalizer_review: countFlag("normalizer_needs_review"),
    validator_issues: countFlag("validator_issues_count")
  };
}
