import { getAvailableColumns, listOptionalRows, tableExists } from "./corpus_tables.js";

export const PROMOTION_COLUMNS = [
  "promotion_id",
  "slot",
  "slot_label",
  "value_type",
  "query_role",
  "display_value",
  "normalized_value",
  "compact_value",
  "numeric_value",
  "date_value",
  "ordinal",
  "confidence",
  "candidate_id",
  "source_path",
  "projection_id",
  "release_fingerprint",
  "materialization_version",
  "is_current"
];

const ROLE_PRIORITY_SQL = "CASE query_role WHEN 'title' THEN 0 WHEN 'identifier' THEN 1 WHEN 'date' THEN 2 WHEN 'actor' THEN 3 ELSE 9 END";

export function hasPromotionSurface(database) {
  return tableExists(database, "document_promotions") && promotionColumns(database).includes("display_value");
}

export function promotionColumns(database) {
  return getAvailableColumns(database, "document_promotions", PROMOTION_COLUMNS);
}

export function listDocumentPromotions(database, docId, limit = 120) {
  const columns = promotionColumns(database);
  if (!columns.includes("slot") || !columns.includes("display_value")) return [];
  const currentWhere = columns.includes("is_current") ? "AND COALESCE(is_current, 1) = 1" : "";
  const orderBy = promotionOrderBy(columns);
  return listOptionalRows(
    database,
    "document_promotions",
    `SELECT ${columns.join(", ")} FROM document_promotions WHERE document_id = ? ${currentWhere} ORDER BY ${orderBy} LIMIT ?`,
    [docId, limit]
  );
}

export function promotionTitle(promotions, fallback = null) {
  return firstPromotionValue(promotions, { roles: ["title"] }) || fallback;
}

export function promotionActor(promotions, fallback = null) {
  return firstPromotionValue(promotions, { roles: ["actor"] }) || fallback;
}

export function promotionDate(promotions, fallback = null) {
  return firstPromotionValue(promotions, { roles: ["date"] }) || fallback;
}

export function promotionSummary(promotions) {
  return promotions
    .filter((promotion) => promotion?.display_value)
    .map((promotion) => `${promotion.slot_label || promotion.slot}: ${promotion.display_value}`)
    .join(" | ");
}

export function promotionSqlExpressions(database, documentAlias = "d") {
  const columns = promotionColumns(database);
  if (!tableExists(database, "document_promotions") || !columns.includes("slot") || !columns.includes("display_value")) {
    return {
      title: "NULL",
      actor: "NULL",
      date: "NULL",
      summary: "NULL",
      text: "NULL"
    };
  }
  const hasQueryRole = columns.includes("query_role");
  const hasSlotLabel = columns.includes("slot_label");
  const currentFlag = columns.includes("is_current") ? "AND COALESCE(p.is_current, 1) = 1" : "";
  const dateValue = columns.includes("date_value") ? "COALESCE(p.date_value, p.display_value)" : "p.display_value";
  const textLabel = hasSlotLabel ? "COALESCE(p.slot_label, p.slot)" : "p.slot";
  const orderBy = promotionOrderBy(columns, "p");
  const docRef = `${documentAlias}.id`;
  const current = `p.document_id = ${docRef} ${currentFlag}`;
  const titleWhere = conditionWithRole(hasQueryRole, "title");
  const actorWhere = conditionWithRole(hasQueryRole, "actor");
  const dateWhere = conditionWithRole(hasQueryRole, "date");
  return {
    title: `(SELECT p.display_value FROM document_promotions p WHERE ${current} AND (${titleWhere}) ORDER BY ${orderBy} LIMIT 1)`,
    actor: `(SELECT p.display_value FROM document_promotions p WHERE ${current} AND (${actorWhere}) ORDER BY ${orderBy} LIMIT 1)`,
    date: `(SELECT ${dateValue} FROM document_promotions p WHERE ${current} AND (${dateWhere}) ORDER BY ${orderBy} LIMIT 1)`,
    summary: `(SELECT GROUP_CONCAT(p.slot || ': ' || p.display_value, ' | ') FROM document_promotions p WHERE ${current})`,
    text: `(SELECT GROUP_CONCAT(${textLabel} || ': ' || p.display_value, ' ') FROM document_promotions p WHERE ${current})`
  };
}

function conditionWithRole(hasQueryRole, role) {
  return hasQueryRole ? `p.query_role = '${role}'` : "0";
}

function promotionOrderBy(columns, alias = "") {
  const prefix = alias ? `${alias}.` : "";
  const parts = [];
  if (columns.includes("query_role")) parts.push(ROLE_PRIORITY_SQL.replace(/\bquery_role\b/g, `${prefix}query_role`));
  if (columns.includes("ordinal")) parts.push(`COALESCE(${prefix}ordinal, 0)`);
  if (columns.includes("promotion_id")) parts.push(`${prefix}promotion_id`);
  return parts.length ? parts.join(", ") : `${prefix}slot`;
}

function firstPromotionValue(promotions, { roles = [] }) {
  const roleSet = new Set(roles);
  const match = promotions.find((promotion) => roleSet.has(String(promotion?.query_role || "")) && promotion?.display_value);
  return match?.display_value || null;
}
