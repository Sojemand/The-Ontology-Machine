import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createMemoryStore } from "../../server/memory.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

test("memory store applies frontend_policy summary truncation", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-memory-policy-"));
  const frontendPolicy = buildDefaultFrontendPolicy();
  frontendPolicy.memory.max_summary_length = 12;
  const store = createMemoryStore({ rootDir: tempDir, getFrontendPolicy: () => frontendPolicy });

  try {
    store.record({ ownerId: "user-1", chatId: "chat-1", userMsg: "Was war?", assistantAnswer: "Das ist eine sehr lange Antwort mit vielen Details." });
    const recent = store.recent({ ownerId: "user-1", limit: 1 });
    assert.ok(recent[0].assistant_summary.length <= 12);
  } finally {
    store.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("memory store applies frontend_policy query stop words", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-memory-policy-"));
  const frontendPolicy = buildDefaultFrontendPolicy();
  frontendPolicy.memory.query_stop_words = [...frontendPolicy.memory.query_stop_words, "telekom"];
  const store = createMemoryStore({ rootDir: tempDir, getFrontendPolicy: () => frontendPolicy });

  try {
    store.record({ ownerId: "user-1", chatId: "chat-1", userMsg: "Telekom Rechnung", assistantAnswer: "Es gibt eine Telekom Rechnung." });
    const result = store.search({ ownerId: "user-1", query: "Telekom" });
    assert.equal(result.results.length, 0);
    assert.match(result.info, /too broad/i);
  } finally {
    store.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
});
