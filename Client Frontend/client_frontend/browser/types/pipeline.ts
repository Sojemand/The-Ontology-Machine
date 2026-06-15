export interface PipelineManagerState {
  available: boolean;
  reason: string;
  pipeline_root?: string;
  mcp_server_dir?: string;
  tool_count?: number;
  kernel_status?: Record<string, unknown> | null;
  semantic_control_kernel_tool_count?: number;
  active_workflow_run?: KernelWorkflowRunSummary | null;
  active_pipeline_run?: PipelineRunState | KernelWorkflowRunSummary | null;
  active_dialog?: KernelDialogState | null;
  active_recovery_event?: KernelMirrorEvent | null;
  pending_kernel_event_count?: number;
  permission_status: {
    active_agent_level?: string;
    default_agent_level?: string;
    maximum_agent_level?: string;
    allowed_tool_count?: number;
    blocked_tool_count?: number;
    level_order?: string[];
  } | null;
  permission_warning: string;
  raw_mcp_tool_count?: number;
}

export interface KernelWorkflowRunSummary {
  run_id?: string;
  workflow_run_id?: string;
  workflow_tool?: string;
  status?: string;
  step_id?: string;
  step_label?: string;
  user_visible_summary?: string;
  updated_at?: string;
}

export interface KernelClientFrontendEventBatch {
  schema_version: "kernel.client_frontend_event_batch.v1";
  cursor: string;
  events: KernelClientFrontendEvent[];
  session_id?: string;
  auto_results?: KernelAutoChatResult[];
}

export interface KernelAutoChatResult {
  answer: string;
  sources: Array<Record<string, unknown>>;
  mode?: "exact" | "lookup" | "analytic";
  exactness?: "exact" | "evidence_grounded" | "ambiguous" | "insufficient_evidence";
  metrics?: {
    scope_documents: number;
    matched_documents: number;
    matched_occurrences: number;
    aggregated_values: Record<string, number | null> | null;
  };
  ambiguities?: Array<{
    slot: string;
    candidate_count: number;
    strategy: string;
  }>;
  method?: string;
}

export interface KernelClientFrontendEvent {
  schema_version: "kernel.client_frontend_event.v1";
  frontend_event_id: string;
  frontend_event_kind: "interaction_request" | "progress_event" | "mirror_event" | "tool_availability" | "interaction_resolved";
  mirror_event_id?: string;
  created_at: string;
  interaction_request?: KernelUserInteractionRequest;
  progress_event?: KernelProgressEvent;
  mirror_event?: KernelMirrorEvent;
  tool_availability?: {
    mirror_event_id: string;
    allowed_agent_tools?: string[];
    status?: string;
    created_at?: string;
    expires_at?: string;
    updated_at?: string;
  };
}

export interface KernelUserInteractionRequest {
  schema_version: "kernel.user_interaction_request.v1";
  interaction_request_id: string;
  workflow_run_id: string;
  function_or_route: string;
  interaction_function: string;
  interaction_kind: string;
  dialog_type:
    | "folder_picker"
    | "folder_create_picker"
    | "text_input"
    | "database_path_picker"
    | "active_database_choice"
    | "database_list_picker"
    | "input_presence_confirmation"
    | "update_mode_choice"
    | "generic_confirmation"
    | "blocker_notice"
    | "progress_notice"
    | "recovery_dialog"
    | "support_bundle_notice";
  target_identity: Record<string, unknown>;
  state_snapshot_identity: Record<string, unknown>;
  user_visible_title: string;
  user_visible_summary: string;
  response_shape: unknown;
  expiration_policy: Record<string, unknown>;
  created_at: string;
  options?: Array<Record<string, unknown>>;
  prefilled_values?: Record<string, unknown>;
  mirror_event_id?: string;
  recovery_id?: string;
  recovery_dialog_type?: string;
  risk_class?: string;
  confirmation_request_id?: string;
}

export interface KernelUserInteractionResponse {
  schema_version: "kernel.user_interaction_response.v1";
  interaction_response_id: string;
  interaction_request_id: string;
  response_status: "submitted" | "cancelled" | "closed" | "expired" | "superseded" | "rejected_stale";
  target_identity: Record<string, unknown>;
  state_snapshot_identity: Record<string, unknown>;
  host_surface_identity: string;
  submitted_at: string;
  path_value?: string;
  text_value?: string;
  choice_id?: string;
  selected_database_paths?: string[];
  confirmation_decision?: string;
  recovery_id?: string;
  cancellation_reason?: string;
}

export interface KernelProgressEvent {
  schema_version: "kernel.progress_event.v1";
  workflow_run_id: string;
  workflow_tool: string;
  step_id: string;
  step_label: string;
  event_type: string;
  status:
    | "step_started"
    | "step_completed"
    | "waiting_for_user"
    | "blocked"
    | "retrying"
    | "cancelled"
    | "completed"
    | "failed";
  sequence_index: number;
  user_visible_summary: string;
  current_state_summary?: string;
  timestamp: string;
  ordinal?: number;
  total_steps?: number;
  attempt_count?: number;
  artifact_refs?: unknown[];
  receipt_refs?: unknown[];
}

export interface KernelRecoveryOption {
  schema_version?: string;
  recovery_id: string;
  label?: string;
  description?: string;
  owner?: string;
  recovery_action_type?: string;
  effect?: string;
  risk_class?: string;
  target_identity?: Record<string, unknown>;
  state_snapshot_identity?: Record<string, unknown>;
  agent_tool?: string;
  kernel_dialog_action?: string;
  starts_new_workflow?: boolean;
  continuation_workflow_tool?: string;
  support_bundle_ref?: unknown;
  expires_at?: string;
}

export interface KernelEventScopedToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, never>;
    required?: string[];
    additionalProperties: false;
  };
}

export interface KernelMirrorEvent {
  schema_version: "kernel.mirror_event.v1";
  mirror_event_id: string;
  mirror_source: string;
  is_kernel_auto_call: boolean;
  event_type: string;
  severity: string;
  user_visible_summary: string;
  current_state_summary?: string;
  workflow_run_id?: string;
  workflow_tool?: string;
  user_visible_cause?: string;
  kernel_dialog_state?: KernelDialogState | Record<string, unknown> | null;
  recovery_event_id?: string;
  recovery_options?: KernelRecoveryOption[];
  allowed_agent_tools?: string[];
  allowed_agent_tool_definitions?: KernelEventScopedToolDefinition[];
  agent_explanation_guidance?: string | Record<string, unknown>;
  technical_detail_ref?: unknown;
  support_bundle_ref?: unknown;
  progress_event?: KernelProgressEvent | null;
}

export interface KernelDialogState {
  interaction_request: KernelUserInteractionRequest | null;
  status: "active" | "stale" | "resolved";
  mirror_event_id?: string;
}

export interface KernelInteractionBridgeResponse {
  schema_version: "semantic_control_kernel.host_bridge_response.v1";
  status: "accepted" | "rejected_stale" | "cancelled" | "closed" | "failed";
  interaction_request_id?: string;
  user_visible_summary: string;
  persisted_response?: KernelUserInteractionResponse;
  error?: {
    code?: string;
    safe_message?: string;
  };
}

export interface KernelInteractionRouteResponse {
  bridge_response: KernelInteractionBridgeResponse;
  event_batch: KernelClientFrontendEventBatch;
  auto_results?: KernelAutoChatResult[];
}

export interface PipelineRunState {
  status: string;
  run_id?: string;
  active_context?: {
    input_folder?: string;
    artifact_folder?: string;
    corpus_output_folder?: string;
    corpus_db_path?: string;
    semantic_release_mode?: string;
  };
  elapsed_seconds?: number;
  mode?: string;
  run_phase?: string;
  processing_started?: boolean;
  input_before_run?: {
    total_files?: number;
    preview_count?: number;
  };
  run_result?: {
    total?: number;
    success?: number;
    errors?: number;
    needs_review?: number;
    retries?: number;
  };
  snapshot?: PipelineRunSnapshot | null;
  preflight_failure?: PipelinePreflightFailure | null;
  no_document_processing?: PipelineNoDocumentProcessing | null;
  latest_run_log?: {
    tail?: string[];
  };
  message?: string;
}

export interface PipelineRunCancelResponse {
  status: string;
  run_cancelled?: boolean;
  run_id?: string;
  pid?: number;
  return_code?: number | null;
  message?: string;
}

export interface KernelRuntimeResetResponse {
  status: string;
  reset_id: string;
  created_at: string;
  archived_path_count: number;
  preserved_paths: string[];
  reason: string;
  background_process_termination?: Record<string, unknown> | null;
  message?: string;
}

export interface PipelinePreflightFailure {
  reason?: string;
  artifact_path?: string;
  scope?: string;
  message?: string;
  modules?: Array<{
    key?: string;
    display_name?: string;
    healthy?: boolean;
    message?: string;
    blocking_dependencies?: Array<{ name?: string; detail?: string }>;
  }>;
}

export interface PipelineNoDocumentProcessing {
  input_files?: number;
  reported_total?: number;
  snapshot_total?: number;
  message?: string;
  preview_files?: Array<{
    relative_path?: string;
    size_bytes?: number;
  }>;
}

export interface PipelineStageSnapshot {
  status?: string;
  detail?: string;
  progress_current?: number;
  progress_total?: number;
  progress_label?: string;
}

export interface PipelineRunSnapshot {
  total?: number;
  completed?: number;
  pending?: number;
  success?: number;
  errors?: number;
  needs_review?: number;
  retries?: number;
  current_file?: string;
  current_attempt?: number;
  current_route_family?: string;
  current_optimizer_module?: string;
  current_interpreter_module?: string;
  current_intake_reason?: string;
  is_running?: boolean;
  aborted?: boolean;
  stage_statuses?: Record<string, PipelineStageSnapshot>;
}
