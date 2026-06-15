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

test("extra embedded recovery definitions are not overexposed when bridge proof narrows the active event", async () => {
  let bridgeCalls = 0;
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => {
      bridgeCalls += 1;
      return {
        schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
        mirror_event_id: "mev_extra_defs",
        recovery_event_id: "rev_extra_defs",
        state_snapshot_id: "ss_extra_defs",
        status: "active",
        tool_definitions: [
          {
            name: "kernel_open_recovery_dialog",
            description: "Open recovery dialog.",
            inputSchema: { type: "object", properties: {}, additionalProperties: false }
          }
        ]
      };
    }
  });

  await adapter.bootstrap();
  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_extra_defs",
    recovery_event_id: "rev_extra_defs",
    state_snapshot_identity: { state_snapshot_id: "ss_extra_defs" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_extra_defs",
        recovery_event_id: "rev_extra_defs",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ],
    allowed_agent_tool_definitions: [
      {
        name: "kernel_open_recovery_dialog",
        description: "Open recovery dialog.",
        inputSchema: { type: "object", properties: {}, additionalProperties: false }
      },
      {
        name: "kernel_open_support_bundle",
        description: "Open support bundle.",
        inputSchema: { type: "object", properties: {}, additionalProperties: false }
      }
    ]
  }));

  await adapter.prepareEventScopedTools({ clientRequestId: "req-extra-defs" });

  assert.equal(bridgeCalls, 1);
  assert.deepEqual(
    adapter.activeEventScopedToolDefinitions().map((tool) => tool.name),
    ["kernel_open_recovery_dialog"]
  );
});

test("recovery tools without Kernel-bound recovery options fail closed before definition lookup", async () => {
  let bridgeCalls = 0;
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => {
      bridgeCalls += 1;
      return {
        schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
        mirror_event_id: "mev_unbound",
        recovery_event_id: "rev_unbound",
        state_snapshot_id: "ss_unbound",
        status: "active",
        tool_definitions: [
          {
            name: "kernel_open_recovery_dialog",
            description: "Open recovery dialog.",
            inputSchema: { type: "object", properties: {}, additionalProperties: false }
          }
        ]
      };
    }
  });

  await adapter.bootstrap();
  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_unbound",
    recovery_event_id: "rev_unbound",
    state_snapshot_identity: { state_snapshot_id: "ss_unbound" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: []
  }));

  await adapter.prepareEventScopedTools({ clientRequestId: "req-unbound" });

  assert.equal(bridgeCalls, 0);
  assert.equal(adapter.activeEventScopedToolDefinitions().length, 0);
});
