import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { pathToFileURL } from "node:url";

import { DEFAULT_CONFIG } from "./types.js";
import { validateRootDir } from "./validation.js";

export class SqlDatabasePathError extends Error {
  constructor(message) {
    super(message);
    this.name = "SqlDatabasePathError";
    this.field = "sql_database_path";
  }
}

export function normalizeStoredSqlDatabasePath(value) {
  if (typeof value !== "string") {
    return "";
  }
  const normalized = value.trim();
  return normalized || "";
}

export function resolveSqlDatabasePath(rootDir, config) {
  const resolvedRootDir = validateRootDir(rootDir);
  const configuredPath = normalizeStoredSqlDatabasePath(config?.sql_database_path);
  if (!configuredPath) {
    throw new SqlDatabasePathError("SQL database path is not configured.");
  }
  return path.resolve(resolvedRootDir, configuredPath);
}

export function resolveSqlDataDir(rootDir, config) {
  return path.dirname(resolveSqlDatabasePath(rootDir, config));
}

export function assertSqlDatabaseAccessible(rootDir, config) {
  const dbPath = resolveSqlDatabasePath(rootDir, config);
  let database = null;

  try {
    database = new DatabaseSync(`${pathToFileURL(dbPath).href}?mode=ro`);
  } catch (error) {
    throw new SqlDatabasePathError(
      `SQL database could not be opened: ${dbPath}${error instanceof Error && error.message ? ` (${error.message})` : ""}`
    );
  }

  try {
    const hasDocumentsTable = database.prepare(
      "SELECT 1 AS present FROM sqlite_master WHERE type = 'table' AND name = 'documents' LIMIT 1"
    ).get();
    if (!hasDocumentsTable?.present) {
      throw new SqlDatabasePathError(`SQL database is incompatible: table 'documents' is missing (${dbPath}).`);
    }
    return { dbPath, dataDir: path.dirname(dbPath) };
  } finally {
    database.close();
  }
}
