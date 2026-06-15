import assert from "node:assert/strict";
import test from "node:test";

import { createPipelineKernelAdapter } from "../../client_frontend/pipeline_agent/kernel_client.js";
import {
  PERMANENT_MCP_TOOLS,
  PERMANENT_AGENT_TOOL_NAMES,
  defaultKernelCallTool,
  mirrorEvent,
  recoveryOption
} from "./pipeline-agent-test-fixtures.js";

test("recovery tools stay out of the permanent tool context until an auto-call mirror event activates them", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({
      status: "active",
      tool_definitions: [{
        name: "kernel_open_recovery_dialog",
        description: "Open recovery dialog.",
        inputSchema: { type: "object", properties: {}, additionalProperties: false }
      }]
    })
  });

  await adapter.bootstrap();
  assert.equal(adapter.toolDefinitions().length, PERMANENT_AGENT_TOOL_NAMES.length);
  assert.equal(adapter.toolDefinitions().some((tool) => tool.name === "kernel_open_recovery_dialog"), false);

  const recoveryMirror = mirrorEvent({
    mirror_event_id: "mev_go_live",
    recovery_event_id: "rev_go_live",
    is_kernel_auto_call: true,
    state_snapshot_identity: { state_snapshot_id: "ss_go_live" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_go_live",
        recovery_event_id: "rev_go_live",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ]
  });
  adapter.ingestMirrorEvent(recoveryMirror);
  await adapter.prepareEventScopedTools();

  assert.equal(adapter.toolDefinitions().some((tool) => tool.name === "kernel_open_recovery_dialog"), true);

  adapter.maybeRetireRecoveryTools(recoveryMirror, {
    status: "rejected",
    error: { code: "event_scope_mismatch" }
  });

  assert.equal(adapter.toolDefinitions().some((tool) => tool.name === "kernel_open_recovery_dialog"), false);
  assert.equal(adapter.toolDefinitions().length, PERMANENT_AGENT_TOOL_NAMES.length);
});
