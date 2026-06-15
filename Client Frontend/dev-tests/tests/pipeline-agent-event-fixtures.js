export function kernelToolResponse(toolName, overrides = {}) {
  return {
    schema_version: "semantic_control_kernel.mcp_response.v1",
    status: "ok",
    tool_name: toolName,
    effect: "read",
    user_visible_summary: `${toolName} completed.`,
    mirror_event: null,
    ...overrides
  };
}

export function hostBridgeResponse(overrides = {}) {
  return {
    schema_version: "semantic_control_kernel.host_bridge_response.v1",
    status: "accepted",
    user_visible_summary: "The Kernel processed the interaction response.",
    ...overrides
  };
}

export function mirrorEvent(overrides = {}) {
  return {
    schema_version: "kernel.mirror_event.v1",
    mirror_event_id: "mev_0001",
    mirror_source: "kernel",
    is_kernel_auto_call: false,
    event_type: "progress",
    severity: "info",
    user_visible_summary: "Kernel mirror summary.",
    current_state_summary: "Kernel state summary.",
    workflow_run_id: "wr_0001",
    workflow_tool: "manual_pipeline_run",
    allowed_agent_tools: [],
    recovery_options: [],
    ...overrides
  };
}

export function recoveryOption(overrides = {}) {
  const agentTool = String(overrides.agent_tool || "kernel_open_recovery_dialog");
  const recoveryId = String(overrides.recovery_id || `rcv_${agentTool}`);
  return {
    schema_version: "kernel.recovery_option.v1",
    recovery_id: recoveryId,
    recovery_event_id: "rev_0001",
    label: `Recovery option ${recoveryId}`,
    description: "Kernel-authored recovery option.",
    owner: "agent_tool",
    recovery_action_type: "open_dialog",
    effect: "opens_kernel_dialog",
    risk_class: "low",
    target_identity: {
      target_hash: "tgt_0001"
    },
    state_snapshot_identity: {
      state_snapshot_id: "ss_0001"
    },
    agent_tool: agentTool,
    kernel_dialog_action: "reopen_dialog",
    starts_new_workflow: false,
    continuation_workflow_tool: null,
    requires_confirmation: false,
    expires_at: "2026-05-06T01:00:00Z",
    ...overrides
  };
}

export function progressEvent(overrides = {}) {
  return {
    schema_version: "kernel.progress_event.v1",
    workflow_run_id: "wr_0001",
    workflow_tool: "manual_pipeline_run",
    step_id: "step_01",
    step_label: "Analyze input",
    event_type: "workflow_step",
    status: "step_started",
    sequence_index: 1,
    user_visible_summary: "Kernel started the step.",
    current_state_summary: "Running",
    timestamp: "2026-05-06T00:00:00Z",
    ...overrides
  };
}

export function interactionRequest(overrides = {}) {
  return {
    schema_version: "kernel.user_interaction_request.v1",
    interaction_request_id: "irq_0001",
    workflow_run_id: "wr_0001",
    function_or_route: "manual_pipeline_run",
    interaction_function: "choose_artifact_root",
    interaction_kind: "selection",
    dialog_type: "folder_picker",
    target_identity: {
      target_hash: "tgt_0001",
      artifact_root_path_hash: "pth_0001"
    },
    state_snapshot_identity: {
      state_snapshot_id: "ss_0001"
    },
    user_visible_title: "Choose folder",
    user_visible_summary: "Choose the workspace folder for this workflow.",
    response_shape: "path_value",
    expiration_policy: {
      policy_id: "selection_short",
      ttl_seconds: 1800
    },
    created_at: "2026-05-06T00:00:00Z",
    options: [],
    ...overrides
  };
}

export function interactionResponse(request, overrides = {}) {
  return {
    schema_version: "kernel.user_interaction_response.v1",
    interaction_response_id: "irs_0001",
    interaction_request_id: request.interaction_request_id,
    response_status: "submitted",
    target_identity: { ...request.target_identity },
    state_snapshot_identity: { ...request.state_snapshot_identity },
    host_surface_identity: "client_frontend_http_pipeline_session",
    submitted_at: "2026-05-06T00:00:00Z",
    path_value: "C:\\Workspace",
    ...overrides
  };
}

export function clientFrontendEvent(kind, payload = {}, overrides = {}) {
  return {
    schema_version: "kernel.client_frontend_event.v1",
    frontend_event_id: `cfe_${kind}_0001`,
    frontend_event_kind: kind,
    mirror_event_id: String(payload?.mirror_event_id || payload?.interaction_request?.mirror_event_id || payload?.mirror_event?.mirror_event_id || "mev_0001"),
    created_at: "2026-05-06T00:00:00Z",
    ...payload,
    ...overrides
  };
}

export function eventBatch(events = [], cursor = "1") {
  return {
    schema_version: "kernel.client_frontend_event_batch.v1",
    cursor,
    events
  };
}
