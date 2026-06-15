import path from "node:path";

import { openRuntimeDatabase } from "../sqlite_runtime.js";
import { validateRootDir } from "./validation.js";

function ensureColumn(db, tableName, columnName, definition) {
  const existingColumns = db.prepare(`PRAGMA table_info(${tableName})`).all();
  if (!existingColumns.some((column) => column.name === columnName)) {
    db.exec(`ALTER TABLE ${tableName} ADD COLUMN ${columnName} ${definition}`);
  }
}

function initializeSchema(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS memories (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      owner_id TEXT NOT NULL DEFAULT '',
      chat_id TEXT NOT NULL,
      user_message TEXT NOT NULL,
      assistant_summary TEXT NOT NULL,
      topics TEXT NOT NULL DEFAULT '[]',
      search_text TEXT NOT NULL DEFAULT '',
      created_at INTEGER NOT NULL
    )
  `);

  ensureColumn(db, "memories", "owner_id", "TEXT NOT NULL DEFAULT ''");
  ensureColumn(db, "memories", "search_text", "TEXT NOT NULL DEFAULT ''");
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_mem_created ON memories(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_mem_owner_created ON memories(owner_id, created_at DESC);
  `);
}

export function createMemoryRepository({ rootDir }) {
  const db = openRuntimeDatabase(path.join(validateRootDir(rootDir), "chats.db"), {
    label: "memory store SQLite database"
  });
  let stmtInsertFts = null;
  let stmtSearchScoped = null;
  let stmtSearchUnscoped = null;

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

  const stmtSelectAll = db.prepare(`
    SELECT id, owner_id, chat_id, user_message, assistant_summary, topics, search_text, created_at
    FROM memories
    ORDER BY id ASC
  `);
  const stmtUpdate = db.prepare(`
    UPDATE memories
    SET owner_id = ?, user_message = ?, assistant_summary = ?, topics = ?, search_text = ?
    WHERE id = ?
  `);
  const stmtInsert = db.prepare(`
    INSERT INTO memories (owner_id, chat_id, user_message, assistant_summary, topics, search_text, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  const stmtRecentAll = db.prepare(`
    SELECT id, owner_id, chat_id, user_message, assistant_summary, topics, search_text, created_at
    FROM memories
    ORDER BY created_at DESC, id DESC
    LIMIT ?
  `);
  const stmtRecentByOwner = db.prepare(`
    SELECT id, owner_id, chat_id, user_message, assistant_summary, topics, search_text, created_at
    FROM memories
    WHERE owner_id = ?
    ORDER BY created_at DESC, id DESC
    LIMIT ?
  `);
  const stmtFindFtsTable = db.prepare(`
    SELECT 1
    FROM sqlite_master
    WHERE type = 'table' AND name = 'memories_fts'
    LIMIT 1
  `);

  function hasSearchIndex() {
    return Boolean(stmtFindFtsTable.get());
  }

  function rebuildSearchIndex() {
    stmtInsertFts = null;
    stmtSearchScoped = null;
    stmtSearchUnscoped = null;
    db.exec("DROP TABLE IF EXISTS memories_fts");
    db.exec(`
      CREATE VIRTUAL TABLE memories_fts
      USING fts5(search_text, tokenize = 'unicode61 remove_diacritics 2')
    `);
    stmtInsertFts = db.prepare(`
      INSERT INTO memories_fts (rowid, search_text)
      VALUES (?, ?)
    `);
    for (const row of db.prepare("SELECT id, search_text FROM memories").all()) {
      stmtInsertFts.run(row.id, row.search_text || "");
    }
  }

  function ensureSearchIndex() {
    if (!stmtInsertFts) {
      rebuildSearchIndex();
    }
  }

  function searchStatement(scoped) {
    ensureSearchIndex();
    if (scoped) {
      stmtSearchScoped ||= db.prepare(`
        SELECT m.id, m.owner_id, m.chat_id, m.user_message, m.assistant_summary, m.topics, m.search_text, m.created_at,
               bm25(memories_fts) AS text_rank
        FROM memories_fts
        JOIN memories m ON m.id = memories_fts.rowid
        WHERE m.owner_id = ?
          AND memories_fts MATCH ?
        ORDER BY bm25(memories_fts), m.created_at DESC, m.id DESC
        LIMIT ?
      `);
      return stmtSearchScoped;
    }
    stmtSearchUnscoped ||= db.prepare(`
      SELECT m.id, m.owner_id, m.chat_id, m.user_message, m.assistant_summary, m.topics, m.search_text, m.created_at,
             bm25(memories_fts) AS text_rank
      FROM memories_fts
      JOIN memories m ON m.id = memories_fts.rowid
      WHERE memories_fts MATCH ?
      ORDER BY bm25(memories_fts), m.created_at DESC, m.id DESC
      LIMIT ?
    `);
    return stmtSearchUnscoped;
  }

  return {
    hasSearchIndex,
    listMemoryRows() {
      return stmtSelectAll.all();
    },
    updateMemoryProjection({ id, ownerId, userMessage, assistantSummary, topicsJson, searchText }) {
      stmtUpdate.run(ownerId, userMessage, assistantSummary, topicsJson, searchText, id);
    },
    rebuildSearchIndex,
    insertMemory({ ownerId, chatId, userMessage, assistantSummary, topicsJson, searchText, createdAt }) {
      ensureSearchIndex();
      const result = stmtInsert.run(ownerId, chatId, userMessage, assistantSummary, topicsJson, searchText, createdAt);
      stmtInsertFts.run(result.lastInsertRowid, searchText);
      return result.lastInsertRowid;
    },
    searchRows({ ownerId, ftsQuery, limit, scoped }) {
      const statement = searchStatement(scoped);
      return scoped ? statement.all(ownerId, ftsQuery, limit) : statement.all(ftsQuery, limit);
    },
    listRecent({ ownerId, limit }) {
      return ownerId ? stmtRecentByOwner.all(ownerId, limit) : stmtRecentAll.all(limit);
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
