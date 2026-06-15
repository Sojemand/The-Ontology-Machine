import assert from "node:assert/strict";
import test from "node:test";

import { OWNER_ID, withChatStore } from "./chat-store-test-fixtures.js";

test("save truncates long titles and strips newlines", () => {
  withChatStore((store) => {
    store.save(OWNER_ID, "chat-1", `${"A".repeat(120)}\nline`, []);
    const result = store.get(OWNER_ID, "chat-1");
    assert.ok(result);
    assert.ok(result.title.length <= 80);
    assert.ok(!result.title.includes("\n"));
    assert.ok(result.title.endsWith("..."));
  });
});

test("save with null title stores an empty string", () => {
  withChatStore((store) => {
    store.save(OWNER_ID, "chat-1", null, []);
    assert.equal(store.get(OWNER_ID, "chat-1")?.title, "");
  });
});
