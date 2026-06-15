import { sanitizeRow } from "./output_policy.js";
import { MAX_SQL_ROWS } from "./types.js";

export function collectCappedRows(statement, params = [], limit = MAX_SQL_ROWS) {
  const rows = [];
  let rowCount = 0;
  for (const row of statement.iterate(...params)) {
    rowCount += 1;
    if (rows.length < limit) rows.push(sanitizeRow(row));
  }
  return { row_count: rowCount, rows, truncated: rowCount > limit };
}

export function assertReadOnlySql(query) {
  const raw = String(query || "").trim();
  if (!raw) throw new Error("sql_query needs an SQL query.");
  const withoutTrailingSemicolon = raw.replace(/;+\s*$/, "");
  if (withoutTrailingSemicolon.includes(";")) throw new Error("Multiple SQL statements are not allowed.");
  if (!/^(select|with)\b/i.test(withoutTrailingSemicolon)) throw new Error("Only SELECT or WITH queries are allowed.");
  if (/\b(insert|update|delete|drop|alter|create|replace|attach|detach|vacuum|reindex|analyze|pragma)\b/i.test(withoutTrailingSemicolon)) {
    throw new Error("The query contains disallowed SQL keywords.");
  }
  return withoutTrailingSemicolon;
}
