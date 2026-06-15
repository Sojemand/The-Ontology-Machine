export function tableExists(database, tableName) {
  return Boolean(database.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?").get(tableName));
}

function getTableColumns(database, tableName) {
  if (!tableExists(database, tableName)) return [];
  return database.prepare(`PRAGMA table_info(${JSON.stringify(tableName)})`).all().map((column) => String(column.name || ""));
}

export function getAvailableColumns(database, tableName, columns) {
  const available = new Set(getTableColumns(database, tableName));
  return columns.filter((column) => available.has(column));
}

export function normalizePathForLookup(value) {
  return String(value || "").trim().replace(/\//g, "\\");
}

export function listStringsFromTable(database, tableName, columnName, docId) {
  if (!tableExists(database, tableName)) return [];
  return database.prepare(`SELECT ${columnName} FROM ${tableName} WHERE document_id = ? ORDER BY ${columnName}`).all(docId).map((row) => row[columnName]).filter(Boolean);
}

export function listOptionalRows(database, tableName, sql, params = []) {
  return tableExists(database, tableName) ? database.prepare(sql).all(...params) : [];
}

export function getOptionalRow(database, tableName, sql, params = []) {
  return tableExists(database, tableName) ? database.prepare(sql).get(...params) || null : null;
}
