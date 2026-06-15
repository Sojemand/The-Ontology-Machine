import path from "node:path";

import { openRuntimeDatabase } from "../sqlite_runtime.js";
import { validateRootDir } from "./validation.js";

function ensureColumn(db, tableName, columnName, definition) {
  const existingColumns = db.prepare(`PRAGMA table_info(${tableName})`).all();
  const hasColumn = existingColumns.some((column) => column.name === columnName);
  if (!hasColumn) {
    db.exec(`ALTER TABLE ${tableName} ADD COLUMN ${columnName} ${definition}`);
  }
}

function initializeSchema(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS chats (
      id TEXT PRIMARY KEY,
      owner_id TEXT NOT NULL DEFAULT '',
      title TEXT NOT NULL DEFAULT '',
      messages TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    )
  `);

  ensureColumn(db, "chats", "owner_id", "TEXT NOT NULL DEFAULT ''");
  db.exec("CREATE INDEX IF NOT EXISTS idx_chats_owner_updated ON chats(owner_id, updated_at DESC)");
}

export function createChatRepository({ rootDir }) {
  const dbPath = path.join(validateRootDir(rootDir), "chats.db");
  const db = openRuntimeDatabase(dbPath, { label: "chat store SQLite database" });
  try {
    initializeSchema(db);
  } catch (error) {
    try {
      db.close();
    } catch {
      // Preserve the initialization error.
    }
    throw error;
  }

  const stmtUpsert = db.prepare(`
    INSERT INTO chats (id, owner_id, title, messages, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      owner_id = excluded.owner_id,
      title = excluded.title,
      messages = excluded.messages,
      updated_at = excluded.updated_at
  `);
  const stmtGet = db.prepare("SELECT * FROM chats WHERE id = ? AND owner_id = ?");
  const stmtList = db.prepare(`
    SELECT id, owner_id, title, messages, created_at, updated_at
    FROM chats
    WHERE owner_id = ?
    ORDER BY updated_at DESC
    LIMIT ?
  `);
  const stmtDelete = db.prepare("DELETE FROM chats WHERE id = ? AND owner_id = ?");

  return {
    findChat(ownerId, chatId) {
      return stmtGet.get(chatId, ownerId) || null;
    },
    listChats(ownerId, limit) {
      return stmtList.all(ownerId, limit);
    },
    saveChat({ chatId, ownerId, title, messages, createdAt, updatedAt }) {
      stmtUpsert.run(chatId, ownerId, title, messages, createdAt, updatedAt);
    },
    deleteChat(ownerId, chatId) {
      return stmtDelete.run(chatId, ownerId).changes > 0;
    },
    close() {
      try {
        db.close();
      } catch {
        // Already closed.
      }
    }
  };
}
