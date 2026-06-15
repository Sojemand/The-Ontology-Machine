import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  createOntologyCallLogger,
  ONTOLOGY_AGENT_CALL_LOG_FILE,
  readOntologyCallLog
} from "../../client_frontend/ontology_agent/call_logger.js";
import { createOntologyAgent } from "../../client_frontend/ontology_agent/workflow.js";

import { cleanupFixture, createFixture } from "../support/ontology-agent-fixtures.js";

test("ontology call logger keeps only the last 100 entries", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-ontology-call-log-"));
  try {
    const logger = createOntologyCallLogger({ stateRoot: tempDir, maxEntries: 100 });
    for (let index = 0; index < 105; index += 1) {
      await logger.record({ event: "probe", sequence: index });
    }
    const log = await readOntologyCallLog(path.join(tempDir, ONTOLOGY_AGENT_CALL_LOG_FILE));
    assert.equal(log.entries.length, 100);
    assert.equal(log.entries[0].sequence, 5);
    assert.equal(log.entries[99].sequence, 104);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("ontology agent logs LLM rounds and tool calls for a chat turn", async () => {
  const fixture = createFixture();
  const stateRoot = path.join(fixture.tempDir, "ontology-agent-state");
  let completionCalls = 0;
  const agent = createOntologyAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    stateRoot,
    runtimeConfig: { context_limit: 128_000, llm_model: "test-chat-model" },
    embedTextsFn: async (_runtimeConfig, texts) => texts.map(() => [0.1, 0.2]),
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
    assert.equal(result.token_usage.estimated, true);
    assert.equal(result.token_usage.llm_calls, 2);
    assert.ok(result.token_usage.input_tokens > 0);
    assert.ok(result.token_usage.output_tokens > 0);
    const log = await readOntologyCallLog(path.join(stateRoot, ONTOLOGY_AGENT_CALL_LOG_FILE));
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
    assert.equal(llmStart.runtime.model, "test-chat-model");
    assert.ok(llmStart.context.approx_tokens > 0);
    const toolStart = log.entries.find((entry) => entry.event === "tool_call_start");
    assert.equal(toolStart.tool_name, "sql_query");
    assert.match(toolStart.arguments.query, /^SELECT id, file_name FROM documents/);
    const toolEnd = log.entries.find((entry) => entry.event === "tool_call_end");
    assert.equal(toolEnd.result.row_counts.rows, 1);
    assert.equal(toolEnd.doc_id_count, 1);
    assert.ok(log.entries.find((entry) => entry.event === "llm_call_end").assistant.approx_output_tokens > 0);
  } finally {
    agent.close();
    cleanupFixture(fixture);
  }
});
