import assert from "node:assert/strict";
import test from "node:test";

import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";
import { createMinimalAgent } from "../../server/min_agent.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture } from "./min-agent-test-fixtures.js";

test("agent uses frontend_policy prompt blocks in the system prompt", async () => {
  const fixture = createTempAgentFixture("vp-min-policy-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      page_count INTEGER DEFAULT 1
    );
  `);
  fixture.database.close();
  fixture.database = null;

  const frontendPolicy = buildDefaultFrontendPolicy();
  frontendPolicy.min_agent.prompt.identity = "Custom system identity.";
  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    frontendPolicy,
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      return { choices: [{ message: { content: "Fertig.", tool_calls: [] } }] };
    }
  });

  try {
    await agent.chat({ message: "Test" });
    assert.match(String(calls[0]?.[0]?.content || ""), /Custom system identity\./);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("agent enforces frontend_policy max_tool_rounds", async () => {
  const fixture = createTempAgentFixture("vp-min-policy-rounds-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      page_count INTEGER DEFAULT 1
    );
  `);
  fixture.database.close();
  fixture.database = null;

  const frontendPolicy = buildDefaultFrontendPolicy();
  frontendPolicy.min_agent.runtime.max_tool_rounds = 1;
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    frontendPolicy,
    createChatCompletionFn: async () => ({
      choices: [{
        message: {
          content: "",
          tool_calls: [{ id: "sql-1", type: "function", function: { name: "sql_query", arguments: JSON.stringify({ query: "SELECT id, file_name FROM documents" }) } }]
        }
      }]
    })
  });

  try {
    await assert.rejects(() => agent.chat({ message: "Test" }), /Too many tool rounds/i);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
