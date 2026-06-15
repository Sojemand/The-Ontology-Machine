import assert from "node:assert/strict";
import test from "node:test";

import { createPipelineKernelAdapter } from "../../client_frontend/pipeline_agent/kernel_client.js";
import {
  createFakeClient,
  defaultKernelCallTool,
  EVENT_SCOPED_RECOVERY_TOOL_NAMES,
  mirrorEvent,
  PERMANENT_MCP_TOOLS,
  recoveryOption
} from "./pipeline-agent-test-fixtures.js";

test("event-scoped tool calls attach hidden event scope outside model-authored arguments", async () => {
  const calls = [];
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => {
      calls.push([name, args]);
      return await defaultKernelCallTool(name, args);
    },
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "mev_scoped",
      recovery_event_id: "rev_scoped",
      state_snapshot_id: "ss_scoped",
      status: "active",
      tool_definitions: [
        {
          name: "kernel_open_recovery_dialog",
          description: "Open recovery dialog.",
          inputSchema: { type: "object", properties: {}, additionalProperties: false }
        }
      ]
    })
  });

  await adapter.bootstrap();
  const recoveryMirror = mirrorEvent({
    mirror_event_id: "mev_scoped",
    recovery_event_id: "rev_scoped",
    state_snapshot_identity: { state_snapshot_id: "ss_scoped" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_scoped",
        recovery_event_id: "rev_scoped",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ]
  });
  adapter.ingestMirrorEvent(recoveryMirror);
  await adapter.prepareEventScopedTools({ conversationRef: "session-1", turnRef: "turn-1", clientRequestId: "req-scoped" });

  const result = await adapter.callEventScopedTool("kernel_open_recovery_dialog", {}, recoveryMirror, {
    conversationRef: "session-1",
    turnRef: "turn-1",
    clientRequestId: "req-scoped",
    toolCallNonce: "nonce-scoped"
  });

  assert.equal(result.tool_name, "kernel_open_recovery_dialog");
  assert.deepEqual(calls.find(([name]) => name === "kernel_open_recovery_dialog")[1], {
    mirror_event_id: "mev_scoped",
    recovery_event_id: "rev_scoped",
    state_snapshot_id: "ss_scoped",
    recovery_id: "rcv_scoped",
    client_request_id: "req-scoped",
    tool_call_nonce: "nonce-scoped",
    conversation_ref: "session-1",
    turn_ref: "turn-1"
  });
});

test("embedded event-scoped recovery definitions are accepted even when the mirror event also allows permanent tools", async () => {
  let bridgeCalls = 0;
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => {
      bridgeCalls += 1;
      throw new Error("embedded definitions should be used before the host-only bridge");
    }
  });

  await adapter.bootstrap();
  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_embedded",
    recovery_event_id: "rev_embedded",
    state_snapshot_identity: { state_snapshot_id: "ss_embedded" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_status", "kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_embedded",
        recovery_event_id: "rev_embedded",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ],
    allowed_agent_tool_definitions: [
      {
        name: "kernel_open_recovery_dialog",
        description: "Open recovery dialog.",
        inputSchema: { type: "object", properties: {}, additionalProperties: false }
      }
    ]
  }));

  await adapter.prepareEventScopedTools({ clientRequestId: "req-embedded" });

  assert.equal(bridgeCalls, 0);
  assert.deepEqual(
    adapter.activeEventScopedToolDefinitions().map((tool) => tool.name),
    ["kernel_open_recovery_dialog"]
  );
});
