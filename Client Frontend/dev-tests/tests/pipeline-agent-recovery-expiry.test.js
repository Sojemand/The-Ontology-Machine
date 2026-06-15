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

test("expired tool availability removes temporary recovery tools", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "mev_expired",
      recovery_event_id: "rev_expired",
      state_snapshot_id: "ss_expired",
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
  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_expired",
    recovery_event_id: "rev_expired",
    state_snapshot_identity: { state_snapshot_id: "ss_expired" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_expired",
        recovery_event_id: "rev_expired",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ]
  }));
  await adapter.prepareEventScopedTools({ clientRequestId: "req-expired" });
  assert.equal(adapter.activeEventScopedToolDefinitions().length, 1);

  adapter.ingestKernelEventBatch({
    schema_version: "kernel.client_frontend_event_batch.v1",
    cursor: "2",
    events: [
      {
        schema_version: "kernel.client_frontend_event.v1",
        frontend_event_id: "cfe_tool_expired",
        frontend_event_kind: "tool_availability",
        mirror_event_id: "mev_expired",
        created_at: "2026-05-06T00:05:00Z",
        tool_availability: {
          mirror_event_id: "mev_expired",
          status: "expired",
          allowed_agent_tools: []
        }
      }
    ]
  });

  assert.equal(adapter.activeEventScopedToolDefinitions().length, 0);
});

test("workflow completion retires stale recovery scope even when the old mirror was mislabelled", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "mev_merge_recovery",
      recovery_event_id: "rev_merge_recovery",
      state_snapshot_id: "ss_merge_recovery",
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
  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_merge_recovery",
    recovery_event_id: "rev_merge_recovery",
    workflow_run_id: "wr_old_merge",
    workflow_tool: "legacy_blocked_merge_route",
    state_snapshot_identity: { state_snapshot_id: "ss_merge_recovery" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_merge_recovery",
        recovery_event_id: "rev_merge_recovery",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ]
  }));
  await adapter.prepareEventScopedTools({ clientRequestId: "req-merge-recovery" });
  assert.equal(adapter.activeEventScopedToolDefinitions().length, 1);

  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_merge_complete",
    workflow_run_id: "wr_new_merge",
    workflow_tool: "database_merge_additive_only",
    event_type: "workflow_completed",
    allowed_agent_tools: ["manual_pipeline_run", "database_modify_taxonomy", "database_modify_projections", "kernel_status"],
    recovery_options: [],
    user_visible_summary: "Database merge is complete."
  }));

  adapter.activeRecoveryMirrorEventId = "mev_merge_recovery";
  assert.equal(adapter.buildStatus({ active_workflow_runs: [] }).active_recovery_event, null);
  assert.equal(adapter.activeEventScopedToolDefinitions().length, 0);
});

test("stale recovery scope removes temporary tools and fails closed", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async () => ({
      schema_version: "semantic_control_kernel.mcp_response.v1",
      status: "rejected",
      tool_name: "kernel_open_recovery_dialog",
      effect: "none",
      user_visible_summary: "Recovery event expired.",
      mirror_event: null,
      error: {
        code: "event_scope_missing",
        category: "contract_validation",
        safe_message: "Recovery event expired."
      }
    }),
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "mev_stale",
      recovery_event_id: "rev_stale",
      state_snapshot_id: "ss_stale",
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
    mirror_event_id: "mev_stale",
    recovery_event_id: "rev_stale",
    state_snapshot_identity: { state_snapshot_id: "ss_stale" },
    event_type: "recovery_state",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [
      recoveryOption({
        recovery_id: "rcv_stale",
        recovery_event_id: "rev_stale",
        agent_tool: "kernel_open_recovery_dialog"
      })
    ]
  });
  adapter.ingestMirrorEvent(recoveryMirror);
  await adapter.prepareEventScopedTools({ clientRequestId: "req-stale" });
  const result = await adapter.callEventScopedTool("kernel_open_recovery_dialog", {}, recoveryMirror, { clientRequestId: "req-stale" });

  assert.equal(result.status, "rejected");
  assert.equal(adapter.activeEventScopedToolDefinitions().length, 0);
});
