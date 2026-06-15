import assert from "node:assert/strict";
import test from "node:test";

import { estimateTokens, estimateMessagesTokens } from "../../server/tokens.js";

// ---------------------------------------------------------------------------
// estimateTokens
// ---------------------------------------------------------------------------

test("estimateTokens returns 0 for empty string", () => {
  assert.equal(estimateTokens(""), 0);
});

test("estimateTokens returns 0 for null/undefined", () => {
  assert.equal(estimateTokens(null), 0);
  assert.equal(estimateTokens(undefined), 0);
});

test("estimateTokens returns correct estimate for short English text", () => {
  const text = "Hello world";
  const tokens = estimateTokens(text);
  // 11 chars / 3.5 = 3.14 â†’ ceil = 4
  assert.equal(tokens, 4);
});

test("estimateTokens returns correct estimate for German compound words", () => {
  const text = "Donaudampfschifffahrtsgesellschaft";
  const tokens = estimateTokens(text);
  // 34 chars / 3.5 = 9.71 â†’ ceil = 10
  assert.equal(tokens, 10);
});

test("estimateTokens handles very long strings", () => {
  const text = "a".repeat(100000);
  const tokens = estimateTokens(text);
  // 100000 / 3.5 = 28571.4 â†’ ceil = 28572
  assert.equal(tokens, 28572);
});

test("estimateTokens handles JSON content", () => {
  const json = JSON.stringify({ rows: [{ id: "doc1", title: "Test" }] });
  const tokens = estimateTokens(json);
  assert.ok(tokens > 0);
  assert.equal(tokens, Math.ceil(json.length / 3.5));
});

test("estimateTokens handles unicode (emoji, CJK)", () => {
  const text = "Hallo Welt ðŸŒ ä½ å¥½ä¸–ç•Œ";
  const tokens = estimateTokens(text);
  assert.ok(tokens > 0);
});

// ---------------------------------------------------------------------------
// estimateMessagesTokens
// ---------------------------------------------------------------------------

test("estimateMessagesTokens returns 0 for empty array", () => {
  assert.equal(estimateMessagesTokens([]), 0);
});

test("estimateMessagesTokens returns 0 for non-array", () => {
  assert.equal(estimateMessagesTokens(null), 0);
  assert.equal(estimateMessagesTokens(undefined), 0);
  assert.equal(estimateMessagesTokens("hello"), 0);
});

test("estimateMessagesTokens adds per-message overhead", () => {
  const messages = [{ role: "user", content: "" }];
  const tokens = estimateMessagesTokens(messages);
  assert.equal(tokens, 4); // 4 overhead + 0 content
});

test("estimateMessagesTokens sums content tokens", () => {
  const messages = [
    { role: "system", content: "Du bist ein Assistent." },
    { role: "user", content: "Hallo" }
  ];
  const tokens = estimateMessagesTokens(messages);
  const expected = 4 + estimateTokens("Du bist ein Assistent.") + 4 + estimateTokens("Hallo");
  assert.equal(tokens, expected);
});

test("estimateMessagesTokens handles null content", () => {
  const messages = [{ role: "assistant", content: null }];
  const tokens = estimateMessagesTokens(messages);
  assert.equal(tokens, 4); // overhead only
});

test("estimateMessagesTokens includes tool_calls arguments", () => {
  const messages = [
    {
      role: "assistant",
      content: null,
      tool_calls: [
        { function: { name: "sql_query", arguments: '{"query":"SELECT * FROM docs"}' } },
        { function: { name: "evidence_search", arguments: '{"query":"Energie"}' } }
      ]
    }
  ];
  const tokens = estimateMessagesTokens(messages);
  const expected =
    4 +
    0 + // null content
    estimateTokens('{"query":"SELECT * FROM docs"}') +
    estimateTokens('{"query":"Energie"}');
  assert.equal(tokens, expected);
});

test("estimateMessagesTokens handles missing tool_calls gracefully", () => {
  const messages = [
    { role: "assistant", content: "OK" },
    { role: "tool", content: '{"result":"data"}', tool_call_id: "abc" }
  ];
  const tokens = estimateMessagesTokens(messages);
  const expected = 4 + estimateTokens("OK") + 4 + estimateTokens('{"result":"data"}');
  assert.equal(tokens, expected);
});

test("estimateMessagesTokens handles many messages", () => {
  const messages = Array.from({ length: 100 }, (_, i) => ({
    role: i % 2 === 0 ? "user" : "assistant",
    content: `Message ${i}`
  }));
  const tokens = estimateMessagesTokens(messages);
  assert.ok(tokens > 400); // 100 * 4 overhead alone
  assert.ok(tokens < 2000);
});

