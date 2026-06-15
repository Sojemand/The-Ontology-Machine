import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalAgent } from "../../server/min_agent.js";
import { createCoverageFixture } from "./min-agent-coverage-fixture.js";
import {
  cleanupAgentFixture,
  createRuntimeConfig
} from "./min-agent-test-fixtures.js";

test("agent can call database_coverage_snapshot as a query tool", async () => {
  const fixture = createCoverageFixture("vp-min-agent-coverage-tool-");
  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "tool-coverage",
                type: "function",
                function: { name: "database_coverage_snapshot", arguments: JSON.stringify({ focus: "promotions", limit: 5 }) }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Die Promotions sind sichtbar.", tool_calls: [] } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Wie sind die Promotions materialisiert?" });
    const toolPayload = JSON.parse(String(calls[1].find((message) => message.role === "tool")?.content || "{}"));
    assert.equal(result.answer, "Die Promotions sind sichtbar.");
    assert.equal(toolPayload.focus, "promotions");
    assert.equal(toolPayload.promotion_coverage.available, true);
    assert.equal(toolPayload.promotion_coverage.slots.some((slot) => slot.slot === "main_character"), true);
    assert.equal(toolPayload.field_coverage, undefined);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
