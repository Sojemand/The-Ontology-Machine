import assert from "node:assert/strict";
import { mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { buildPipelineSystemPrompt } from "../../client_frontend/pipeline_agent/prompt.js";
import { createPipelineKernelAdapter } from "../../client_frontend/pipeline_agent/kernel_client.js";
import { createPipelineManagerAgent } from "../../client_frontend/pipeline_agent/workflow.js";
import {
  createFakeClient,
  createPipelineRoot,
  defaultKernelCallTool,
  eventBatch,
  kernelToolResponse,
  mirrorEvent,
  NON_KERNEL_MCP_TOOLS,
  PERMANENT_AGENT_TOOL_NAMES,
  PERMANENT_MCP_TOOLS,
  recoveryOption
} from "./pipeline-agent-test-fixtures.js";

test("pipeline manager status reports only the permanent tools even when recovery tools are temporarily injected", async () => {
  const root = createPipelineRoot();
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
              frontend_event_id: "cfe_recovery",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_recovery",
              created_at: "2026-05-06T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_recovery",
                recovery_event_id: "rev_recovery",
                state_snapshot_identity: { state_snapshot_id: "ss_0001" },
                event_type: "recovery_state",
                allowed_agent_tools: ["kernel_open_recovery_dialog"],
                recovery_options: [
                  recoveryOption({
                    recovery_id: "rcv_recovery",
                    recovery_event_id: "rev_recovery",
                    agent_tool: "kernel_open_recovery_dialog"
                  })
                ]
              })
            }
          ]);
        }
        if (name === "kernel_list_event_scoped_tool_definitions") {
          return {
            schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
            mirror_event_id: "mev_recovery",
            recovery_event_id: "rev_recovery",
            state_snapshot_id: "ss_0001",
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
    createChatCompletionFn: async () => ({ choices: [{ message: { content: "Recovery options noted." } }] })
  });

  try {
    await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });
    await agent.chat({ message: "What can I do next?", history: [], ownerId: "pipeline-session" });

    const status = await agent.status();

    assert.equal(status.tool_count, PERMANENT_AGENT_TOOL_NAMES.length);
    assert.equal(status.semantic_control_kernel_tool_count, PERMANENT_AGENT_TOOL_NAMES.length);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("pipeline manager surfaces a frontend warning when event-scoped tool definitions cannot be proven for the active recovery event", async () => {
  const root = createPipelineRoot();
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
              frontend_event_id: "cfe_missing_defs",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_missing_defs",
              created_at: "2026-05-06T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_missing_defs",
                recovery_event_id: "rev_missing_defs",
                state_snapshot_identity: { state_snapshot_id: "ss_0001" },
                event_type: "recovery_state",
                allowed_agent_tools: ["kernel_open_recovery_dialog"],
                recovery_options: [
                  recoveryOption({
                    recovery_id: "rcv_missing_defs",
                    recovery_event_id: "rev_missing_defs",
                    agent_tool: "kernel_open_recovery_dialog"
                  })
                ]
              })
            }
          ]);
        }
        if (name === "kernel_list_event_scoped_tool_definitions") {
          return {
            schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
            mirror_event_id: "mev_missing_defs",
            recovery_event_id: "rev_missing_defs",
            state_snapshot_id: "ss_0001",
            status: "unavailable",
            tool_definitions: []
          };
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async () => ({ choices: [{ message: { content: "Recovery options noted." } }] })
  });

  try {
    await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });
    await agent.chat({ message: "What can I do next?", history: [], ownerId: "pipeline-session" });

    const status = await agent.status();

    assert.equal(status.permission_warning, "event_scoped_tool_definitions_unavailable");
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
