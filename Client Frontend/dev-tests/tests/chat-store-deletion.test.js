import assert from "node:assert/strict";
import test from "node:test";

import { OTHER_OWNER_ID, OWNER_ID, withChatStore } from "./chat-store-test-fixtures.js";

test("delete removes only the owner's own chat", () => {
  withChatStore((store) => {
    store.save(OWNER_ID, "chat-1", "Mine", [{ role: "user", content: "Hi" }]);
    store.save(OTHER_OWNER_ID, "chat-2", "Other", [{ role: "user", content: "Nope" }]);

    assert.equal(store.delete(OWNER_ID, "chat-2"), false);
    assert.ok(store.get(OTHER_OWNER_ID, "chat-2"));
    assert.equal(store.delete(OWNER_ID, "chat-1"), true);
    assert.equal(store.get(OWNER_ID, "chat-1"), null);
  });
});

test("delete returns false for non-existent chat", () => {
  withChatStore((store) => {
    assert.equal(store.delete(OWNER_ID, "nonexistent"), false);
  });
});
