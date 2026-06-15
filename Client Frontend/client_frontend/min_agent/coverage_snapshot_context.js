import { cleanArtifactFileName } from "./output_policy.js";
import { getAvailableColumns, tableExists } from "./corpus_tables.js";

export const FOCUS_VALUES = new Set(["overview", "promotions", "fields", "rows", "weak_spots", "release"]);
export const DEFAULT_LIMIT = 20;
export const MAX_LIMIT = 100;
export const GENERIC_VALUES = new Set(["", "other", "unknown", "uncategorized", "unclassified", "none", "n/a"]);

export function createCoverageContext(database) {
  const tableCache = new Map();
  const columnCache = new Map();

  function hasTable(tableName) {
    if (!tableCache.has(tableName)) tableCache.set(tableName, tableExists(database, tableName));
    return tableCache.get(tableName);
  }

  function columns(tableName, columnNames) {
    const key = `${tableName}:${columnNames.join(",")}`;
    if (!columnCache.has(key)) columnCache.set(key, getAvailableColumns(database, tableName, columnNames));
    return columnCache.get(key);
  }

  function hasColumns(tableName, columnNames) {
    return columns(tableName, columnNames).length === columnNames.length;
  }

  function count(tableName, whereSql = "", params = []) {
    if (!hasTable(tableName)) return 0;
    return numberValue(database.prepare(`SELECT COUNT(*) AS count FROM ${tableName}${whereSql}`).get(...params)?.count);
  }

  function countWhereColumns(tableName, predicate) {
    if (!hasTable(tableName)) return 0;
    const tableColumns = columns(tableName, predicate.columns);
    if (!tableColumns.length) return 0;
    return numberValue(database.prepare(predicate.sql(tableColumns)).get()?.count);
  }

  function grouped(tableName, groupColumns, { where = "", orderBy = "row_count DESC", limit = DEFAULT_LIMIT } = {}) {
    if (!hasTable(tableName) || !hasColumns(tableName, groupColumns)) return [];
    const columnList = groupColumns.join(", ");
    return database.prepare(`
      SELECT ${columnList}, COUNT(*) AS row_count
      FROM ${tableName}
      ${where}
      GROUP BY ${columnList}
      ORDER BY ${orderBy}
      LIMIT ?
    `).all(limit).map((row) => normalizeRow(row));
  }

  function activeDocumentWhere(alias = "") {
    const prefix = alias ? `${alias}.` : "";
    return hasColumns("documents", ["is_archived"]) ? ` WHERE COALESCE(${prefix}is_archived, 0) = 0` : "";
  }

  function currentPromotionWhere(alias = "") {
    const prefix = alias ? `${alias}.` : "";
    return hasColumns("document_promotions", ["is_current"]) ? `WHERE COALESCE(${prefix}is_current, 1) = 1` : "";
  }

  function currentPromotionCount() {
    return count("document_promotions", currentPromotionWhere() ? ` ${currentPromotionWhere()}` : "");
  }

  function currentPromotionDocumentCount() {
    if (!hasColumns("document_promotions", ["document_id"])) return 0;
    return numberValue(database.prepare(`SELECT COUNT(DISTINCT document_id) AS count FROM document_promotions ${currentPromotionWhere()}`).get()?.count);
  }

  function currentPromotionSlotCount() {
    if (!hasColumns("document_promotions", ["slot"])) return 0;
    return numberValue(database.prepare(`SELECT COUNT(DISTINCT slot) AS count FROM document_promotions ${currentPromotionWhere()}`).get()?.count);
  }

  return {
    database,
    activeDocumentWhere,
    columns,
    count,
    countWhereColumns,
    currentPromotionCount,
    currentPromotionDocumentCount,
    currentPromotionSlotCount,
    currentPromotionWhere,
    grouped,
    hasColumns,
    hasTable
  };
}

export function normalizeFocus(value) {
  const focus = String(value || "overview").trim().toLowerCase();
  return FOCUS_VALUES.has(focus) ? focus : "overview";
}

export function normalizeLimit(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return DEFAULT_LIMIT;
  return Math.min(MAX_LIMIT, Math.max(1, Math.floor(number)));
}

export function normalizeRow(row = {}) {
  return Object.fromEntries(Object.entries(row).map(([key, value]) => [key, normalizeValue(value)]));
}

export function normalizeDocumentRow(row = {}) {
  const normalized = normalizeRow(row);
  if (normalized.file_name) normalized.file_name = cleanArtifactFileName(normalized.file_name, normalized);
  return normalized;
}

export function normalizeValue(value) {
  if (typeof value === "bigint") return Number(value);
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  return value ?? null;
}

export function numberValue(value) {
  return Number(value || 0);
}

export function rankedCounts(counts, keyName, limit) {
  return Array.from(counts.entries())
    .map(([key, count]) => ({ [keyName]: key, row_count: count }))
    .sort((left, right) => right.row_count - left.row_count || String(left[keyName]).localeCompare(String(right[keyName])))
    .slice(0, limit);
}

export function containsLimitSizedList(value, limit) {
  if (Array.isArray(value)) return value.length >= limit;
  if (value && typeof value === "object") return Object.values(value).some((child) => containsLimitSizedList(child, limit));
  return false;
}
