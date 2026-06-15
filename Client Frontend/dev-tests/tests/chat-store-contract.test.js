import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { openRuntimeDatabase, RUNTIME_SQLITE_BUSY_TIMEOUT_MS } from "../../client_frontend/sqlite_runtime.js";
import { createChatStore } from "../../server/chat_store.js";
import { createChatStore as createChatStoreSurface } from "../../server/chat_store/surface.js";

function makeTempDir() {
  return mkdtempSync(path.join(os.tmpdir(), "vp-chatstore-contract-"));
}

test("chat_store facade re-exports the stable surface factory", () => {
  assert.equal(createChatStore, createChatStoreSurface);
});

test("runtime sqlite helper enables WAL and bounded busy timeout", () => {
  const tempDir = makeTempDir();
  const db = openRuntimeDatabase(path.join(tempDir, "runtime.db"), { label: "test runtime database" });
  try {
    assert.equal(String(db.prepare("PRAGMA journal_mode").get().journal_mode).toLowerCase(), "wal");
    assert.equal(db.prepare("PRAGMA busy_timeout").get().timeout, RUNTIME_SQLITE_BUSY_TIMEOUT_MS);
  } finally {
    db.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("chat store initializes chats.db in WAL mode", () => {
  const tempDir = makeTempDir();
  const store = createChatStore({ rootDir: tempDir });
  try {
    store.save("user-1", "chat-1", "Hallo", [{ role: "user", content: "Hi" }]);
    store.close();
    const db = new DatabaseSync(path.join(tempDir, "chats.db"));
    try {
      assert.equal(String(db.prepare("PRAGMA journal_mode").get().journal_mode).toLowerCase(), "wal");
    } finally {
      db.close();
    }
  } finally {
    store.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("corrupt stored messages fall back to empty arrays and zero counts", () => {
  const tempDir = makeTempDir();
  let store = createChatStore({ rootDir: tempDir });
  try {
    store.save("user-1", "chat-1", "Hallo", [{ role: "user", content: "Hi" }]);
    store.close();

    const db = new DatabaseSync(path.join(tempDir, "chats.db"));
    db.prepare("UPDATE chats SET messages = ? WHERE id = ?").run("{broken-json", "chat-1");
    db.close();

    store = createChatStore({ rootDir: tempDir });
    assert.deepEqual(store.get("user-1", "chat-1")?.messages, []);
    assert.equal(store.list("user-1")[0]?.message_count, 0);
  } finally {
    store.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
});
