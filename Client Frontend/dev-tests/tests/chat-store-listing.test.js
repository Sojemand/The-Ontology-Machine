import assert from "node:assert/strict";
import test from "node:test";

import { OTHER_OWNER_ID, OWNER_ID, withChatStore } from "./chat-store-test-fixtures.js";

test("list returns only chats for the requested owner in updated order", () => {
  withChatStore((store) => {
    store.save(OWNER_ID, "a", "Alpha", [{ role: "user", content: "A" }]);
    store.save(OTHER_OWNER_ID, "foreign", "Foreign", [{ role: "user", content: "F" }]);
    store.save(OWNER_ID, "b", "Beta", [{ role: "user", content: "B" }]);
    store.save(OWNER_ID, "a", "Alpha updated", [
      { role: "user", content: "A" },
      { role: "assistant", content: "A reply" }
    ]);

    const list = store.list(OWNER_ID);
    assert.equal(list.length, 2);
    assert.deepEqual(list.map((entry) => entry.id), ["a", "b"]);
    assert.equal(list[0].message_count, 2);
  });
});

test("list caps at 100 entries and honors custom limit", () => {
  withChatStore((store) => {
    for (let index = 0; index < 120; index += 1) {
      store.save(OWNER_ID, `chat-${index}`, `Chat ${index}`, [{ role: "user", content: `Message ${index}` }]);
    }
    assert.equal(store.list(OWNER_ID).length, 100);
    assert.equal(store.list(OWNER_ID, 3).length, 3);
  });
});

test("list returns empty array when owner is missing or has no chats", () => {
  withChatStore((store) => {
    assert.deepEqual(store.list(OWNER_ID), []);
    assert.deepEqual(store.list(""), []);
  });
});
