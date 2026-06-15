import { DatabaseSync } from "node:sqlite";

export const RUNTIME_SQLITE_BUSY_TIMEOUT_MS = 5000;
const SQLITE_LOCK_RETRY_MS = 100;

export function openRuntimeDatabase(dbPath, { label = "runtime SQLite database" } = {}) {
  const deadline = Date.now() + RUNTIME_SQLITE_BUSY_TIMEOUT_MS;
  while (true) {
    const database = new DatabaseSync(dbPath, { timeout: RUNTIME_SQLITE_BUSY_TIMEOUT_MS });
    try {
      configureRuntimeDatabase(database, label);
      return database;
    } catch (error) {
      try {
        database.close();
      } catch {
        // Preserve the initialization error.
      }
      if (!isLockedDatabaseError(error) || Date.now() >= deadline) {
        throw error;
      }
      sleepSync(SQLITE_LOCK_RETRY_MS);
    }
  }
}

function configureRuntimeDatabase(database, label) {
  database.exec(`PRAGMA busy_timeout = ${RUNTIME_SQLITE_BUSY_TIMEOUT_MS}`);
  const journalMode = database.prepare("PRAGMA journal_mode = WAL").get()?.journal_mode;
  if (String(journalMode || "").toLowerCase() !== "wal") {
    throw new Error(`Unable to enable WAL mode for ${label}: ${journalMode || "unknown"}`);
  }
}

function isLockedDatabaseError(error) {
  return error?.code === "ERR_SQLITE_ERROR" && /database is (locked|busy)/i.test(String(error?.message || ""));
}

function sleepSync(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}
