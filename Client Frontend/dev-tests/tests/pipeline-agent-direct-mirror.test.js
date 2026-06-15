import assert from "node:assert/strict";
import { rmSync } from "node:fs";
import test from "node:test";

import { createPipelineKernelAdapter } from "../../client_frontend/pipeline_agent/kernel_client.js";
import { createPipelineManagerAgent } from "../../client_frontend/pipeline_agent/workflow.js";
import {
  clientFrontendEvent,
  createFakeClient,
  createPipelineRoot,
  defaultKernelCallTool,
  eventBatch,
  hostBridgeResponse,
  interactionRequest,
  interactionResponse,
  kernelToolResponse,
  mirrorEvent,
  PERMANENT_MCP_TOOLS,
  progressEvent,
  recoveryOption
} from "./pipeline-agent-test-fixtures.js";

test("direct tool-return mirror events are stored as Kernel state without creating user intent", async () => {
  const root = createPipelineRoot();
  let completionCalls = 0;
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 50_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        if (name === "kernel_status") {
          return {
            schema_version: "semantic_control_kernel.mcp_response.v1",
            status: "ok",
            tool_name: "kernel_status",
            effect: "read",
            user_visible_summary: "Kernel status read.",
            mirror_event: mirrorEvent({
              mirror_event_id: "mev_direct",
              is_kernel_auto_call: false,
              event_type: "progress"
            })
          };
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async () => {
      completionCalls += 1;
      if (completionCalls === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "tool-1",
                function: {
                  name: "kernel_status",
                  arguments: "{}"
                }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Kernel status captured." } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "status", history: [] });
    const kernelEntries = result.history.filter((entry) => entry.role === "kernel");

    assert.equal(kernelEntries.length, 1);
    assert.equal(kernelEntries[0].kernel_mirror_event.mirror_event_id, "mev_direct");
    assert.equal(result.history.some((entry) => entry.role === "user" && /Kernel mirror/.test(entry.content)), false);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("explain_now auto-call can trigger one agent response without a synthetic user message", async () => {
  const root = createPipelineRoot();
  let completionCalls = 0;
  let providerTools = null;
  let providerMessages = [];
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        if (name === "kernel_list_client_frontend_events") {
          return eventBatch([
            {
              schema_version: "kernel.client_frontend_event.v1",
              frontend_event_id: "cfe_auto",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_auto",
              created_at: "2026-05-06T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_auto",
                recovery_event_id: "rev_auto",
                is_kernel_auto_call: true,
                state_snapshot_identity: { state_snapshot_id: "ss_auto" },
                event_type: "recovery_state",
                allowed_agent_tools: ["kernel_open_recovery_dialog"],
                recovery_options: [
                  recoveryOption({
                    recovery_id: "rcv_auto",
                    recovery_event_id: "rev_auto",
                    agent_tool: "kernel_open_recovery_dialog"
                  })
                ],
                agent_explanation_guidance: { response_mode: "explain_now" }
              })
            }
          ]);
        }
        if (name === "kernel_list_event_scoped_tool_definitions") {
          return {
            schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
            mirror_event_id: "mev_auto",
            recovery_event_id: "rev_auto",
            state_snapshot_id: "ss_auto",
            status: "active",
            tool_definitions: [{
              name: "kernel_open_recovery_dialog",
              description: "Open recovery dialog.",
              inputSchema: { type: "object", properties: {}, additionalProperties: false }
            }]
          };
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async (_runtimeConfig, messages, tools) => {
      completionCalls += 1;
      providerMessages = Array.isArray(messages) ? messages.map((message) => ({ ...message })) : [];
      providerTools = Array.isArray(tools) ? [...tools] : tools;
      return { choices: [{ message: { content: "The Kernel exposed a recovery dialog." } }] };
    }
  });

  try {
    const result = await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });

    assert.equal(result.autoResults.length, 1);
    assert.equal(result.autoResults[0].answer, "The Kernel exposed a recovery dialog.");
    assert.equal(result.autoResults[0].history.some((entry) => entry.role === "user"), false);
    assert.equal(completionCalls, 1);
    assert.deepEqual(providerTools, []);
    assert.match(String(providerMessages[0]?.content || ""), /explanation-only mode/i);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
