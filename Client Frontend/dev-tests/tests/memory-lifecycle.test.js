import assert from "node:assert/strict";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { createMemoryStore } from "../../server/memory.js";
import { cleanupTempDir, makeTempDir, withMemoryStore } from "./memory-test-fixtures.js";

test("recent returns most recent first", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Erste Frage", "Erste Antwort.");
    store.record("chat-1", "Zweite Frage", "Zweite Antwort.");
    store.record("chat-2", "Dritte Frage", "Dritte Antwort.");
    const memories = store.recent(2);
    assert.equal(memories.length, 2);
    assert.match(memories[0].user_message, /Dritte/);
    assert.match(memories[1].user_message, /Zweite/);
  });
});

test("recent returns empty array when no memories exist", () => {
  withMemoryStore((store) => {
    assert.deepEqual(store.recent(), []);
  });
});

test("memories persist across store instances (same DB)", () => {
  const tempDir = makeTempDir();
  try {
    const store1 = createMemoryStore({ rootDir: tempDir });
    store1.record("chat-1", "Frage eins", "Antwort eins.");
    store1.close();

    const store2 = createMemoryStore({ rootDir: tempDir });
    try {
      const memories = store2.recent(5);
      assert.equal(memories.length, 1);
      assert.equal(memories[0].user_message, "Frage eins");
    } finally {
      store2.close();
    }
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("memory store initializes shared chats.db in WAL mode", () => {
  const tempDir = makeTempDir();
  const store = createMemoryStore({ rootDir: tempDir });
  try {
    store.record("chat-1", "Frage eins", "Antwort eins.");
    store.close();
    const db = new DatabaseSync(path.join(tempDir, "chats.db"));
    try {
      assert.equal(String(db.prepare("PRAGMA journal_mode").get().journal_mode).toLowerCase(), "wal");
    } finally {
      db.close();
    }
  } finally {
    store.close();
    cleanupTempDir(tempDir);
  }
});

test("close can be called multiple times safely", () => {
  withMemoryStore((store) => {
    store.close();
    store.close();
    store.close();
  });
});
