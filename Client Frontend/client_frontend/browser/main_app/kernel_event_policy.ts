import type {
  KernelClientFrontendEventBatch,
  KernelDialogState,
  KernelInteractionBridgeResponse,
  KernelMirrorEvent,
  KernelProgressEvent,
  KernelUiState,
  KernelUserInteractionRequest,
  KernelUserInteractionResponse
} from "./types.ts";
import { isKernelRecoveryMirror } from "./kernel_mirror_policy.ts";
import {
  isTerminalKernelProgressStatus
} from "./kernel_progress_presentation.ts";
export {
  buildKernelProgressPresentation,
  isTerminalKernelProgressStatus
} from "./kernel_progress_presentation.ts";
export type { KernelProgressPresentation } from "./kernel_progress_presentation.ts";

const TERMINAL_PROGRESS_VISIBILITY_MS = 10000;
const RESPONSE_VALUE_FIELDS = [
  "path_value",
  "text_value",
  "choice_id",
  "selected_database_paths",
  "confirmation_decision",
  "recovery_id",
  "cancellation_reason"
] as const;

export function applyKernelEventBatchToState(currentState: KernelUiState, batch: KernelClientFrontendEventBatch): KernelUiState {
  let nextState: KernelUiState = {
    ...currentState,
    cursor: batch.cursor || currentState.cursor
  };
  for (const event of Array.isArray(batch.events) ? batch.events : []) {
    const kind = String(event.frontend_event_kind || "");
    if (kind === "interaction_request" && event.interaction_request) {
      nextState = {
        ...nextState,
        activeDialog: {
          interaction_request: event.interaction_request,
          status: "active",
          mirror_event_id: String(event.mirror_event_id || event.interaction_request.mirror_event_id || "")
        },
        dialogStatusText: "",
        pendingInteraction: null,
        localWorkflowActivity: null
      };
    }
    if (kind === "interaction_resolved") {
      nextState = {
        ...nextState,
        activeDialog: null,
        dialogStatusText: "",
        pendingInteraction: null
      };
    }
    if (kind === "progress_event" && event.progress_event) {
      nextState = applyKernelProgressEvent(nextState, event.progress_event);
    }
    if (kind === "mirror_event" && event.mirror_event) {
      nextState = applyKernelMirrorEvent(nextState, event.mirror_event);
    }
  }
  return nextState;
}

export function applyKernelInteractionResponseToState(currentState: KernelUiState, response: KernelInteractionBridgeResponse): KernelUiState {
  const status = String(response?.status || "");
  if (status === "accepted" || status === "cancelled" || status === "closed") {
    return {
      ...currentState,
      activeDialog: null,
      dialogStatusText: String(response.user_visible_summary || ""),
      pendingInteraction: null,
      localWorkflowActivity: status === "accepted" ? currentState.localWorkflowActivity : null
    };
  }
  if (status === "rejected_stale" && currentState.activeDialog) {
    return {
      ...currentState,
      activeDialog: {
        ...currentState.activeDialog,
          status: "stale"
        },
      dialogStatusText: String(response.error?.safe_message || response.user_visible_summary || ""),
      pendingInteraction: null,
      localWorkflowActivity: null
    };
  }
  return {
    ...currentState,
    dialogStatusText: String(response.error?.safe_message || response.user_visible_summary || ""),
    pendingInteraction: null,
    localWorkflowActivity: null
  };
}

export function buildKernelInteractionResponsePayload(
  request: KernelUserInteractionRequest,
  valuePayload: Partial<KernelUserInteractionResponse>,
  responseStatus: KernelUserInteractionResponse["response_status"] = "submitted"
): KernelUserInteractionResponse {
  const presentFields = RESPONSE_VALUE_FIELDS.filter((field) => valuePayload[field] !== undefined);
  if (responseStatus === "submitted" && presentFields.length !== 1) {
    throw new Error("Exactly one dialog response value field must be set.");
  }
  return {
    schema_version: "kernel.user_interaction_response.v1",
    interaction_response_id: `irs_${Math.random().toString(16).slice(2, 10)}`,
    interaction_request_id: request.interaction_request_id,
    response_status: responseStatus,
    target_identity: { ...request.target_identity },
    state_snapshot_identity: { ...request.state_snapshot_identity },
    host_surface_identity: "client_frontend_http_pipeline_session",
    submitted_at: new Date().toISOString(),
    ...valuePayload
  };
}

export function buildKernelCancelPayload(
  request: KernelUserInteractionRequest,
  responseStatus: KernelUserInteractionResponse["response_status"] = "cancelled",
  cancellationReason = "user_cancelled"
): KernelUserInteractionResponse {
  return buildKernelInteractionResponsePayload(request, { cancellation_reason: cancellationReason }, responseStatus);
}

function applyKernelMirrorEvent(currentState: KernelUiState, mirrorEvent: KernelMirrorEvent): KernelUiState {
  const nextState: KernelUiState = {
    ...currentState,
    latestMirrorEvent: mirrorEvent
  };
  if (isKernelRecoveryMirror(mirrorEvent)) {
    nextState.activeRecoveryEvent = mirrorEvent;
  } else if (isCompletedWorkflowMirror(mirrorEvent)) {
    nextState.activeRecoveryEvent = null;
  }
  if (mirrorEvent.progress_event) {
    return applyKernelProgressEvent(nextState, mirrorEvent.progress_event);
  }
  return nextState;
}

function isCompletedWorkflowMirror(mirrorEvent: KernelMirrorEvent): boolean {
  return String(mirrorEvent.event_type || "") === "workflow_completed";
}

function applyKernelProgressEvent(currentState: KernelUiState, progressEvent: KernelProgressEvent): KernelUiState {
  const currentLatest = currentState.latestProgressEvent;
  const sameWorkflow = currentLatest?.workflow_run_id === progressEvent.workflow_run_id;
  const nextSequence = Number(progressEvent.sequence_index || 0);
  const currentSequence = Number(currentLatest?.sequence_index || 0);
  if (sameWorkflow && nextSequence < currentSequence) {
    return currentState;
  }
  const filtered = currentState.progressEvents.filter((event) => {
    return !(event.workflow_run_id === progressEvent.workflow_run_id && event.step_id === progressEvent.step_id);
  });
  const refreshTerminalHold = isTerminalKernelProgressStatus(progressEvent.status)
    && (!sameWorkflow || nextSequence > currentSequence);
  return {
    ...currentState,
    latestProgressEvent: progressEvent,
    progressEvents: [...filtered, progressEvent].sort((left, right) => Number(left.sequence_index || 0) - Number(right.sequence_index || 0)),
    localWorkflowActivity: null,
    terminalProgressVisibleUntilMs: refreshTerminalHold
      ? Date.now() + TERMINAL_PROGRESS_VISIBILITY_MS
      : currentState.terminalProgressVisibleUntilMs
  };
}
