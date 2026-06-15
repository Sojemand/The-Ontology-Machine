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

test("cached status does not keep a stale waiting_for_user workflow without an active dialog", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args = {}) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => [...PERMANENT_MCP_TOOLS],
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "",
      recovery_event_id: "",
      state_snapshot_id: "",
      status: "active",
      tool_definitions: []
    })
  });

  await adapter.bootstrap();
  adapter.ingestProgressEvent(progressEvent({
    workflow_run_id: "wr_waiting",
    workflow_tool: "empty_database_no_semantic_release",
    status: "waiting_for_user",
    step_id: "dc_collect_target",
    step_label: "dc_collect_target",
    user_visible_summary: "Enter the database name for Artifact Tree Kernel Test."
  }));

  const status = adapter.cachedStatus();

  assert.equal(status.active_workflow_run, null);
  assert.equal(status.active_dialog, null);
});

test("cached status does not keep a stale step_completed workflow without a live kernel surface", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args = {}) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => [...PERMANENT_MCP_TOOLS],
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "",
      recovery_event_id: "",
      state_snapshot_id: "",
      status: "active",
      tool_definitions: []
    })
  });

  await adapter.bootstrap();
  adapter.ingestProgressEvent(progressEvent({
    workflow_run_id: "wr_step_completed",
    workflow_tool: "empty_database_no_semantic_release",
    status: "step_completed",
    step_id: "dc_create_empty_database",
    step_label: "dc_create_empty_database",
    user_visible_summary: "dc_create_empty_database completed."
  }));

  const status = adapter.cachedStatus();

  assert.equal(status.active_workflow_run, null);
});

test("terminal workflow mirrors retire stale running progress fallback", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args = {}) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => [...PERMANENT_MCP_TOOLS],
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "",
      recovery_event_id: "",
      state_snapshot_id: "",
      status: "active",
      tool_definitions: []
    })
  });

  await adapter.bootstrap();
  adapter.ingestProgressEvent(progressEvent({
    workflow_run_id: "wr_merge_terminal",
    workflow_tool: "database_merge_additive_only",
    status: "step_started",
    step_id: "kernel_background_continuation",
    step_label: "kernel_background_continuation",
    user_visible_summary: "Kernel workflow continuation started in the background."
  }));
  assert.equal(adapter.cachedStatus().active_workflow_run?.status, "step_started");

  adapter.ingestMirrorEvent(mirrorEvent({
    mirror_event_id: "mev_merge_terminal",
    event_type: "workflow_completed",
    workflow_run_id: "wr_merge_terminal",
    workflow_tool: "database_merge_additive_only",
    user_visible_summary: "Merge completed.",
    current_state_summary: "semantic_release_active"
  }));
  adapter.ingestProgressEvent(progressEvent({
    workflow_run_id: "wr_merge_terminal",
    workflow_tool: "database_merge_additive_only",
    status: "step_started",
    step_id: "kernel_background_continuation",
    step_label: "kernel_background_continuation",
    sequence_index: 2,
    user_visible_summary: "Stale progress replay."
  }));

  assert.equal(adapter.cachedStatus().active_workflow_run, null);
});

test("kernel_status reconciliation clears stale dialog and waiting progress when Kernel has no active surface", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args = {}) => await defaultKernelCallTool(name, args),
    listKernelTools: async () => [...PERMANENT_MCP_TOOLS],
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "",
      recovery_event_id: "",
      state_snapshot_id: "",
      status: "active",
      tool_definitions: []
    })
  });

  await adapter.bootstrap();
  adapter.ingestKernelEventBatch(eventBatch([
    clientFrontendEvent("progress_event", {
      progress_event: progressEvent({
        workflow_run_id: "wr_stale_dialog",
        workflow_tool: "empty_database_default_taxonomy_default_projections",
        status: "waiting_for_user",
        step_id: "dc_collect_target",
        step_label: "dc_collect_target",
        user_visible_summary: "Choose the parent folder for the new Artifact Tree."
      })
    }),
    clientFrontendEvent("interaction_request", {
      interaction_request: interactionRequest({
        interaction_request_id: "irq_stale_dialog",
        workflow_run_id: "wr_stale_dialog",
        function_or_route: "empty_database_default_taxonomy_default_projections",
        interaction_function: "choose_artifact_root_folder"
      })
    })
  ], "1"));

  const before = adapter.cachedStatus();
  const after = await adapter.status({ clientRequestId: "req-status-reconcile" });

  assert.equal(before.active_dialog?.interaction_request?.interaction_request_id, "irq_stale_dialog");
  assert.equal(after.active_workflow_run, null);
  assert.equal(after.active_dialog, null);
  assert.equal(adapter.cachedStatus().active_dialog, null);
});
