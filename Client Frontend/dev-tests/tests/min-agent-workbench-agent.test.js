import assert from "node:assert/strict";
import test from "node:test";

import { assertReadOnlyWorkbench, createMinimalAgent } from "../../server/min_agent.js";
import { cleanupWorkbenchFixture, createWorkbenchFixture } from "./min-agent-workbench-test-fixtures.js";

test("agent can use powershell workbench within allowed corpus scope", async () => {
  const fixture = createWorkbenchFixture();
  const calls = [];
  const agent = createMinimalAgent({
    ...fixture,
    runtimeConfig: {
      llm_model: "gpt-5.4-mini",
      context_limit: 60_096,
      llm_api_key: "",
      embedding_api_key: ""
    },
    runWorkbenchFn: async (options) => {
      assertReadOnlyWorkbench(options.runtime, options.code, options);
      return { ok: true, runtime: "powershell", exit_code: 0, command: "powershell.exe", stdout: "\"allowed note\"", stderr: "" };
    },
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "wb-1",
                type: "function",
                function: { name: "workbench", arguments: JSON.stringify({ runtime: "powershell", code: "Get-Content (Join-Path $env:MIN_AGENT_DATA_DIR 'notes.txt') | ConvertTo-Json -Compress" }) }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Workbench hat die Notiz gelesen.", tool_calls: [] } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Lies die Notiz" });
    const toolPayload = String(calls[1].at(-1).content || "");
    assert.equal(result.answer, "Workbench hat die Notiz gelesen.");
    assert.match(toolPayload, /allowed note/);
    assert.doesNotMatch(toolPayload, /"error"/);
  } finally {
    agent.close();
    cleanupWorkbenchFixture(fixture.rootDir);
  }
});

test("agent receives structured workbench refusal for blocked powershell access", async () => {
  const fixture = createWorkbenchFixture();
  const calls = [];
  const agent = createMinimalAgent({
    ...fixture,
    runtimeConfig: {
      llm_model: "gpt-5.4-mini",
      context_limit: 60_096,
      llm_api_key: "",
      embedding_api_key: ""
    },
    runWorkbenchFn: async (options) => {
      assertReadOnlyWorkbench(options.runtime, options.code, options);
      return { ok: true, runtime: "powershell", exit_code: 0, command: "powershell.exe", stdout: "", stderr: "" };
    },
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "wb-1",
                type: "function",
                function: { name: "workbench", arguments: JSON.stringify({ runtime: "powershell", code: "Get-Content '..\\secret.txt'" }) }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Fallback auf sichere Tools noetig.", tool_calls: [] } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Versuch den Zugriff" });
    const toolPayload = String(calls[1].at(-1).content || "");
    assert.equal(result.answer, "Fallback auf sichere Tools noetig.");
    assert.match(toolPayload, /PowerShell/);
    assert.match(toolPayload, /sql_query|get_document|semantic_search/);
  } finally {
    agent.close();
    cleanupWorkbenchFixture(fixture.rootDir);
  }
});
