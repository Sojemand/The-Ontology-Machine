import { getTableInfo } from "./write_preflight_schema.js";
import { validateInsertReferences, registerCreatedRow } from "./write_preflight_refs.js";
import { addError, defaultRepairForColumn } from "./write_preflight_report.js";
import { cleanIdentifier, isBlankValue, parseInsert, parseUpdateColumns, writeOperation } from "./write_preflight_sql.js";

export function preflightStatement(state, statement, index) {
  const sql = String(statement?.sql || "");
  const tableName = String(statement?.tableName || "");
  const params = Array.isArray(statement?.params) ? statement.params : [];
  const tableInfo = getTableInfo(state.database, tableName);
  if (!tableInfo.exists) {
    addError(state, "table_missing", index, tableName, `Table '${tableName}' does not exist.`, "Run schema creation/migration before ontology writes.");
    return;
  }
  const operation = writeOperation(sql);
  if (operation === "insert" || operation === "replace") {
    preflightInsert(state, tableInfo, sql, params, index, tableName);
    return;
  }
  if (operation === "update") {
    validateKnownColumns(state, tableInfo, parseUpdateColumns(sql), index, tableName);
  }
}

function preflightInsert(state, tableInfo, sql, params, index, tableName) {
  const parsed = parseInsert(sql, params);
  if (!parsed) {
    addError(state, "insert_parse_failed", index, tableName, `Could not parse INSERT/REPLACE columns and VALUES for '${tableName}'.`, "Use a simple explicit column list and VALUES clause.");
    return;
  }
  validateKnownColumns(state, tableInfo, parsed.columns, index, tableName);
  validateNotNullInsertFields(state, tableInfo, parsed, index, tableName);
  validateInsertReferences(state, tableName, parsed, index);
  registerCreatedRow(state, tableName, parsed);
}

function validateKnownColumns(state, tableInfo, columns, index, tableName) {
  for (const column of columns) {
    const cleanColumn = cleanIdentifier(column);
    if (!tableInfo.columns.has(cleanColumn)) {
      addError(
        state,
        "unknown_column",
        index,
        tableName,
        `Column '${cleanColumn}' does not exist on ${tableName}.`,
        cleanColumn.toUpperCase() === "CURRENT_TIMESTAMP"
          ? "CURRENT_TIMESTAMP belongs in the VALUES expression, not in the INSERT column list."
          : `Read PRAGMA table_info(${tableName}) and remove or rename the column.`
      );
    }
  }
}

function validateNotNullInsertFields(state, tableInfo, parsed, index, tableName) {
  const provided = new Set(parsed.columns.map((column) => cleanIdentifier(column)));
  for (const column of tableInfo.rows) {
    const columnName = String(column.name || "");
    if (!columnName) continue;
    if (provided.has(columnName)) {
      validateProvidedNotNullValue(state, parsed, index, tableName, columnName);
      continue;
    }
    if (Number(column.notnull || 0) !== 1 || column.dflt_value !== null && column.dflt_value !== undefined) continue;
    addError(
      state,
      "missing_not_null_column",
      index,
      tableName,
      `${tableName}.${columnName} is NOT NULL and has no default, but the INSERT omits it.`,
      defaultRepairForColumn(tableName, columnName)
    );
  }
}

function validateProvidedNotNullValue(state, parsed, index, tableName, columnName) {
  const value = parsed.valuesByColumn.get(columnName);
  if (!value?.known || !isBlankValue(value.value)) return;
  addError(
    state,
    "null_required_column",
    index,
    tableName,
    `${tableName}.${columnName} is required but the batch provides NULL or an empty value.`,
    defaultRepairForColumn(tableName, columnName)
  );
}
