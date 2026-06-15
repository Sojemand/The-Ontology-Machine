import { eventBatch, hostBridgeResponse, kernelToolResponse } from "./pipeline-agent-event-fixtures.js";
import { EMPTY_OBJECT_SCHEMA, EVENT_SCOPED_RECOVERY_TOOL_NAMES } from "./pipeline-agent-tool-fixtures.js";

export async function defaultKernelCallTool(name, args = {}) {
  if (name === "kernel_status") {
    return kernelToolResponse(name, {
      active_state: {
        support_status: "read_only",
        active_workflow_runs: [],
        active_workflow_run_count: 0,
        resumable_workflow_count: 0,
        pending_interaction_count: 0
      }
    });
  }
  if (name === "kernel_resume_state") {
    return kernelToolResponse(name, {
      resume_state: {
        support_status: "read_only",
        resumable_workflows: [],
        resumable_count: 0,
        resume_options: [],
        next_agent_tool: null,
        id_policy: "kernel_ids_are_opaque"
      }
    });
  }
  if (name === "kernel_continue_resumable_workflow") {
    return kernelToolResponse(name, {
      effect: "none",
      status: "blocked",
      active_state: {
        resume_options: [],
        next_agent_tool: "kernel_continue_resumable_workflow"
      },
      error: {
        code: "resume_option_ref_required",
        category: "contract_validation",
        safe_message: "A specific Kernel resume option is required before a workflow can be continued."
      },
      user_visible_summary: "A specific Kernel resume option is required before a workflow can be continued."
    });
  }
  if (name === "kernel_cancel_active_run") {
    return kernelToolResponse(name, {
      effect: "none",
      cancel_status: "no_active_run",
      user_visible_summary: "No active Kernel workflow run is currently cancellable."
    });
  }
  if (name === "kernel_list_client_frontend_events") {
    return eventBatch([]);
  }
  if (name === "kernel_submit_user_interaction_response") {
    return hostBridgeResponse({
      persisted_response: args.response
    });
  }
  if (name === "kernel_cancel_user_interaction") {
    return hostBridgeResponse({
      status: args.response_status === "closed" ? "closed" : "cancelled"
    });
  }
  if (name === "kernel_list_event_scoped_tool_definitions") {
    return {
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: String(args.mirror_event_id || ""),
      recovery_event_id: String(args.recovery_event_id || ""),
      state_snapshot_id: String(args.state_snapshot_id || ""),
      status: "active",
      tool_definitions: EVENT_SCOPED_RECOVERY_TOOL_NAMES.map((toolName) => ({
        name: toolName,
        description: `Recovery tool ${toolName}.`,
        inputSchema: { ...EMPTY_OBJECT_SCHEMA }
      }))
    };
  }
  return kernelToolResponse(name);
}
