import assert from "node:assert/strict";
import test from "node:test";

import { runPipelineAgentChat } from "../../client_frontend/pipeline_agent/chat_workflow.js";
import { buildTaxonomyWorkflowCommand } from "../../client_frontend/browser/main_app/taxonomy_workflow_launcher.ts";

const TOOL_DEFINITIONS = [
  {
    name: "manual_pipeline_run",
    description: "Run the configured manual pipeline workflow.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  },
  {
    name: "reset_database",
    description: "Start the guarded Kernel database reset path.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  }
];

function baseArgs(overrides = {}) {
  return {
    history: [],
    root: "C:\\Pipeline",
    toolDefinitions: TOOL_DEFINITIONS,
    availabilityStatus: { available: true, toolCount: 16 },
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    ...overrides
  };
}

test("workflow menu command routes directly to the selected Kernel tool without a model round", async () => {
  const calls = [];
  let modelCalls = 0;
  const result = await runPipelineAgentChat(baseArgs({
    message: buildTaxonomyWorkflowCommand("manual_pipeline_run"),
    createChatCompletionFn: async () => {
      modelCalls += 1;
      return { choices: [{ message: { content: "This should not run." } }] };
    },
    callKernelToolFromModel: async (toolName, args) => {
      calls.push({ toolName, args });
      return {
        schema_version: "semantic_control_kernel.mcp_response.v1",
        status: "active",
        tool_name: toolName,
        effect: "workflow_started",
        user_visible_summary: "Manual pipeline workflow started."
      };
    }
  }));

  assert.equal(modelCalls, 0);
  assert.deepEqual(calls, [{ toolName: "manual_pipeline_run", args: {} }]);
  assert.equal(result.answer, "Manual pipeline workflow started.");
});

test("reset database workflow menu command routes directly without a model round", async () => {
  const calls = [];
  let modelCalls = 0;
  const result = await runPipelineAgentChat(baseArgs({
    message: buildTaxonomyWorkflowCommand("reset_database"),
    createChatCompletionFn: async () => {
      modelCalls += 1;
      return { choices: [{ message: { content: "This should not run." } }] };
    },
    callKernelToolFromModel: async (toolName, args) => {
      calls.push({ toolName, args });
      return {
        schema_version: "semantic_control_kernel.mcp_response.v1",
        status: "active",
        tool_name: toolName,
        effect: "workflow_started",
        user_visible_summary: "Database reset workflow started."
      };
    }
  }));

  assert.equal(modelCalls, 0);
  assert.deepEqual(calls, [{ toolName: "reset_database", args: {} }]);
  assert.equal(result.answer, "Database reset workflow started.");
});

test("repeated workflow starter tool calls are not executed twice in one turn", async () => {
  const calls = [];
  let modelCalls = 0;
  const result = await runPipelineAgentChat(baseArgs({
    message: "Run the manual pipeline.",
    createChatCompletionFn: async () => {
      modelCalls += 1;
      return {
        choices: [{
          message: {
            content: "",
            tool_calls: [{
              id: `call-${modelCalls}`,
              type: "function",
              function: {
                name: "manual_pipeline_run",
                arguments: "{}"
              }
            }]
          }
        }]
      };
    },
    callKernelToolFromModel: async (toolName, args) => {
      calls.push({ toolName, args });
      return {
        schema_version: "semantic_control_kernel.mcp_response.v1",
        status: "active",
        tool_name: toolName,
        effect: "workflow_started",
        user_visible_summary: "Manual pipeline workflow started."
      };
    }
  }));

  assert.equal(modelCalls, 2);
  assert.deepEqual(calls, [{ toolName: "manual_pipeline_run", args: {} }]);
  assert.equal(result.answer, "Manual pipeline workflow started.");
});
