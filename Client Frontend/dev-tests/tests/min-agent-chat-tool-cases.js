import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalAgent } from "../../server/min_agent.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture, insertDocument } from "./min-agent-test-fixtures.js";

test("agent returns after the first answer once tool work is complete", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-");
  insertDocument(fixture.database);
  fixture.database.close();
  fixture.database = null;

  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages.map((message) => ({ role: message.role, content: message.content })));
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "tool-1",
                type: "function",
                function: { name: "sql_query", arguments: JSON.stringify({ query: "SELECT id, file_name, file_path FROM documents WHERE id = 'doc-1'" }) }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Es gibt 1 Stromrechnung.", tool_calls: [] } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Wie viele Stromrechnungen gibt es?" });
    assert.equal(result.answer, "Es gibt 1 Stromrechnung.");
    assert.equal(result.sources.length, 1);
    assert.equal(calls.length, 2);
    assert.equal(result.token_usage.estimated, true);
    assert.equal(result.token_usage.llm_calls, 2);
    assert.ok(result.token_usage.input_tokens > 0);
    assert.ok(result.token_usage.output_tokens > 0);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("sql tool output redacts local artifact paths and normalized JSON filenames", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-redacted-");
  insertDocument(fixture.database, {
    file_name: "alpha.structured.normalized.json",
    file_path: "C:\\Users\\Norma\\Desktop\\File Optimzer\\Artefacts\\Documents\\normalized\\alpha.structured.normalized.json"
  });
  fixture.database.close();
  fixture.database = null;

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
                id: "tool-1",
                type: "function",
                function: { name: "sql_query", arguments: JSON.stringify({ query: "SELECT id, file_name, file_path FROM documents WHERE id = 'doc-1'" }) }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "OK", tool_calls: [] } }] };
    }
  });

  try {
    await agent.chat({ message: "Zeige eine Beispieldatei" });
    const toolPayload = JSON.parse(String(calls[1].find((message) => message.role === "tool")?.content || "{}"));
    assert.equal(toolPayload.rows[0].file_name, "alpha");
    assert.equal(toolPayload.rows[0].file_path, "corpus://document/doc-1");
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
