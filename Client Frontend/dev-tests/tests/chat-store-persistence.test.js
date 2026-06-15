import assert from "node:assert/strict";
import test from "node:test";

import { OTHER_OWNER_ID, OWNER_ID, withChatStore } from "./chat-store-test-fixtures.js";

test("save and get returns the same messages", () => {
  withChatStore((store) => {
    const messages = [
      { role: "user", content: "Hallo" },
      { role: "assistant", content: "Guten Tag!" }
    ];
    store.save(OWNER_ID, "chat-1", "Hallo", messages);

    const result = store.get(OWNER_ID, "chat-1");
    assert.ok(result);
    assert.equal(result.id, "chat-1");
    assert.equal(result.title, "Hallo");
    assert.deepEqual(result.messages, messages);
    assert.ok(result.created_at > 0);
    assert.ok(result.updated_at >= result.created_at);
  });
});

test("get returns null for non-existent or foreign chat", () => {
  withChatStore((store) => {
    store.save(OWNER_ID, "chat-1", "Hallo", [{ role: "user", content: "Hi" }]);
    assert.equal(store.get(OWNER_ID, "nonexistent"), null);
    assert.equal(store.get(OTHER_OWNER_ID, "chat-1"), null);
  });
});

test("save updates existing chat for the same owner", () => {
  withChatStore((store) => {
    store.save(OWNER_ID, "chat-1", "First", [{ role: "user", content: "First" }]);
    const first = store.get(OWNER_ID, "chat-1");

    store.save(OWNER_ID, "chat-1", "Updated", [
      { role: "user", content: "First" },
      { role: "assistant", content: "Reply" }
    ]);
    const updated = store.get(OWNER_ID, "chat-1");

    assert.ok(updated);
    assert.equal(updated.title, "Updated");
    assert.equal(updated.messages.length, 2);
    assert.equal(updated.created_at, first.created_at);
    assert.ok(updated.updated_at >= first.updated_at);
  });
});

test("save handles unicode content and empty messages", () => {
  withChatStore((store) => {
    const messages = [
      { role: "user", content: "Umlaut ae oe ue ss" },
      { role: "assistant", content: "Symbols still roundtrip" }
    ];
    store.save(OWNER_ID, "chat-1", "Short title", messages);
    store.save(OWNER_ID, "chat-2", "", []);

    const first = store.get(OWNER_ID, "chat-1");
    const second = store.get(OWNER_ID, "chat-2");
    assert.deepEqual(first.messages, messages);
    assert.deepEqual(second.messages, []);
    assert.equal(store.list(OWNER_ID).find((entry) => entry.id === "chat-2")?.message_count, 0);
  });
});

test("close can be called multiple times safely", () => {
  withChatStore((store) => {
    store.close();
    store.close();
    store.close();
  });
});
