import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  createQueryCallLogger,
  QUERY_AGENT_CALL_LOG_FILE,
  readQueryCallLog
} from "../../client_frontend/min_agent/call_logger.js";
import { createMinimalAgent } from "../../server/min_agent.js";

import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture, insertDocument } from "./min-agent-test-fixtures.js";

test("query call logger keeps only the last 100 entries", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-query-call-log-"));
  try {
    const logger = createQueryCallLogger({ stateRoot: tempDir, maxEntries: 100 });
    for (let index = 0; index < 105; index += 1) {
      await logger.record({ event: "probe", sequence: index });
    }
    const log = await readQueryCallLog(path.join(tempDir, QUERY_AGENT_CALL_LOG_FILE));
    assert.equal(log.entries.length, 100);
    assert.equal(log.entries[0].sequence, 5);
    assert.equal(log.entries[99].sequence, 104);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("query agent logs LLM rounds and tool calls for a chat turn", async () => {
  const fixture = createTempAgentFixture("vp-query-agent-call-log-");
  insertDocument(fixture.database);
  fixture.database.close();
  fixture.database = null;
  const stateRoot = path.join(fixture.tempDir, "query-agent-state");
  let completionCalls = 0;
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    stateRoot,
    runtimeConfig: createRuntimeConfig({ llm_provider: "openrouter", llm_model: "test-query-model" }),
    createChatCompletionFn: async () => {
      completionCalls += 1;
      if (completionCalls === 1) {
        return {
          choices: [{
            message: {
              role: "assistant",
              content: "",
              tool_calls: [{
                id: "call-sql-1",
                type: "function",
                function: {
                  name: "sql_query",
                  arguments: JSON.stringify({ query: "SELECT id, file_name FROM documents ORDER BY id" })
                }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { role: "assistant", content: "I checked the corpus." } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Check the corpus." });
    assert.equal(result.answer, "I checked the corpus.");
    assert.equal(result.token_usage.llm_calls, 2);
    const log = await readQueryCallLog(path.join(stateRoot, QUERY_AGENT_CALL_LOG_FILE));
    const events = log.entries.map((entry) => entry.event);
    assert.deepEqual(events, [
      "turn_start",
      "llm_call_start",
      "llm_call_end",
      "tool_call_start",
      "tool_call_end",
      "llm_call_start",
      "llm_call_end",
      "turn_final"
    ]);
    const llmStart = log.entries.find((entry) => entry.event === "llm_call_start");
    assert.equal(llmStart.runtime.provider, "openrouter");
    assert.equal(llmStart.runtime.model, "test-query-model");
    assert.equal(llmStart.request.tool_count > 0, true);
    const toolEnd = log.entries.find((entry) => entry.event === "tool_call_end");
    assert.equal(toolEnd.result.row_counts.rows, 1);
    assert.equal(toolEnd.doc_id_count, 1);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("query agent logs provider errors during a chat turn", async () => {
  const fixture = createTempAgentFixture("vp-query-agent-call-error-");
  insertDocument(fixture.database);
  fixture.database.close();
  fixture.database = null;
  const stateRoot = path.join(fixture.tempDir, "query-agent-state");
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    stateRoot,
    runtimeConfig: createRuntimeConfig({ llm_provider: "openrouter", llm_model: "openrouter/owl-alpha" }),
    createChatCompletionFn: async () => {
      throw new Error("[provider:chat_completion] Provider returned error");
    }
  });

  try {
    await assert.rejects(
      () => agent.chat({ message: "Was steht in der DB?" }),
      /Provider returned error/
    );
    const log = await readQueryCallLog(path.join(stateRoot, QUERY_AGENT_CALL_LOG_FILE));
    assert.equal(log.entries.some((entry) => entry.event === "llm_call_error"), true);
    const errorEntry = log.entries.find((entry) => entry.event === "llm_call_error");
    assert.match(errorEntry.error.message, /Provider returned error/);
    assert.equal(errorEntry.runtime.provider, "openrouter");
    assert.equal(errorEntry.runtime.model, "openrouter/owl-alpha");
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
