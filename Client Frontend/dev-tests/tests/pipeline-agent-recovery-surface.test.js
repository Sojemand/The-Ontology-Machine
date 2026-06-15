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

test("recovery tools are absent from the normal model-visible surface", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({})
  });

  await adapter.bootstrap();

  assert.equal(adapter.toolDefinitions().some((tool) => EVENT_SCOPED_RECOVERY_TOOL_NAMES.includes(tool.name)), false);
});

test("a recovery mirror event injects only the allowed event-scoped tools", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "mev_allowed",
      recovery_event_id: "rev_allowed",
      state_snapshot_id: "ss_allowed",
      status: "active",
      tool_definitions: [
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
    })
  });

  await adapter.bootstrap();
  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_allowed",
    recovery_event_id: "rev_allowed",
    state_snapshot_identity: { state_snapshot_id: "ss_allowed" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog", "kernel_open_support_bundle"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_dialog",
        recovery_event_id: "rev_allowed",
        agent_tool: "kernel_open_recovery_dialog"
      }),
      recoveryOption({
        recovery_id: "rcv_support",
        recovery_event_id: "rev_allowed",
        agent_tool: "kernel_open_support_bundle",
        support_bundle_ref: { support_bundle_id: "sb_allowed" }
      })
    ]
  }));

  await adapter.prepareEventScopedTools({ clientRequestId: "req-allowed" });

  assert.deepEqual(
    adapter.activeEventScopedToolDefinitions().map((tool) => tool.name),
    ["kernel_open_recovery_dialog", "kernel_open_support_bundle"]
  );
});
