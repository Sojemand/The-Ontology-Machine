import assert from "node:assert/strict";
import test from "node:test";

import { applyDisplayedSources, extractLatestAssistantSources, mapRestoredMessages, sumMessageTokenUsage } from "../../src/main_app/state_domain.ts";
import { createInitialViewerState } from "../../src/main_app/state_domain.ts";
import { source } from "./main-app-fixtures.js";

test("mapRestoredMessages normalizes raw roles into the visible ui contract", () => {
  const messages = mapRestoredMessages([
    { role: "ignored", content: "System" },
    { role: "user", content: "Frage" },
    { role: "assistant", content: "Antwort", sources: [source()] }
  ]);

  assert.deepEqual(messages.map((message) => message.role), ["system", "user", "assistant"]);
  assert.equal(messages[2].sources[0].id, "doc-1");
});

test("state domain keeps matching source selection and latest assistant sources visible", () => {
  const latestMessages = [
    { role: "assistant", content: "Alt {{cite:doc:doc-a}}", sources: [source({ id: "doc-a", file_name: "a.pdf" })] },
    { role: "assistant", content: "Neu {{cite:doc:doc-b}}", sources: [source({ id: "doc-b", file_name: "b.pdf" })] }
  ];
  const next = applyDisplayedSources(
    { ...createInitialViewerState(), selectedSource: source({ id: "doc-b", page_count: 3 }), page: 99, imageFailed: true },
    [source({ id: "doc-a" }), source({ id: "doc-b", page_count: 3 })]
  );

  assert.equal(extractLatestAssistantSources(latestMessages).at(0)?.id, "doc-b");
  assert.equal(next.viewer.selectedSource?.id, "doc-b");
  assert.equal(next.viewer.page, 3);
  assert.equal(next.viewer.imageFailed, false);
});

test("state domain aggregates assistant token usage for the visible session", () => {
  const total = sumMessageTokenUsage([
    { role: "system", content: "Welcome" },
    { role: "user", content: "Frage" },
    { role: "assistant", content: "A", token_usage: { estimated: true, input_tokens: 1000, output_tokens: 80 } },
    { role: "assistant", content: "B", token_usage: { estimated: true, input_tokens: 2500, output_tokens: 120 } }
  ]);

  assert.deepEqual(total, { inputTokens: 3500, outputTokens: 200 });
});
