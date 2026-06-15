import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createChatStore } from "../../server/chat_store.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

test("chat store uses frontend_policy title and history caps", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-chat-policy-"));
  const frontendPolicy = buildDefaultFrontendPolicy();
  frontendPolicy.chat_history.max_history = 2;
  frontendPolicy.chat_history.title_max_length = 12;
  const store = createChatStore({ rootDir: tempDir, getFrontendPolicy: () => frontendPolicy });

  try {
    for (let index = 0; index < 5; index += 1) {
      store.save("owner-1", `chat-${index}`, `Sehr langer Titel Nummer ${index}`, []);
    }
    assert.ok(store.get("owner-1", "chat-0")?.title.length <= 12);
    assert.equal(store.list("owner-1", 10).length, 2);
  } finally {
    store.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
});
