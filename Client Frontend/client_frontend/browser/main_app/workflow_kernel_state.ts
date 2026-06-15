import { isTerminalKernelProgressStatus } from "./kernel_event_policy.ts";
import { createInitialKernelUiState } from "./state_domain.ts";
import type { AppState } from "./types.ts";

const LOCAL_WORKFLOW_ACTIVITY_HOLD_MS = 10000;

export function isLocalWorkflowActivityActive(state: AppState): boolean {
  const activity = state.kernelUi.localWorkflowActivity;
  return Boolean(activity && (!activity.expiresAtMs || activity.expiresAtMs > Date.now()));
}

export function hasTerminalProgressHold(state: AppState): boolean {
  return Boolean(state.kernelUi.terminalProgressVisibleUntilMs && state.kernelUi.terminalProgressVisibleUntilMs > Date.now());
}

export function hasRetainedKernelProgress(state: AppState): boolean {
  const latest = state.kernelUi.latestProgressEvent;
  if (!latest) return false;
  return !isTerminalKernelProgressStatus(latest.status) || hasTerminalProgressHold(state);
}

export function hasLocalKernelSurface(state: AppState): boolean {
  return Boolean(state.kernelUi.pendingInteraction || isLocalWorkflowActivityActive(state) || hasRetainedKernelProgress(state));
}

export function pruneExpiredLocalWorkflowActivity(state: AppState): void {
  const activity = state.kernelUi.localWorkflowActivity;
  if (!activity || state.kernelUi.pendingInteraction) return;
  if (activity.expiresAtMs && activity.expiresAtMs <= Date.now()) {
    state.kernelUi.localWorkflowActivity = null;
  }
}

export function reconcileLocalWorkflowActivityWithRealKernelState(state: AppState): void {
  pruneExpiredLocalWorkflowActivity(state);
  if (!state.kernelUi.localWorkflowActivity) return;
  const manager = state.health?.pipeline_manager;
  if (state.kernelUi.latestProgressEvent || manager?.active_workflow_run || manager?.active_pipeline_run) {
    state.kernelUi.localWorkflowActivity = null;
  }
}

export function startLocalWorkflowActivity(
  state: AppState,
  activity: {
    activityId: string;
    title: string;
    summary: string;
    workflowRunId?: string;
    workflowTool?: string;
  }
): void {
  const now = Date.now();
  state.kernelUi.localWorkflowActivity = {
    activityId: activity.activityId,
    title: activity.title,
    summary: activity.summary,
    state: "running",
    workflowRunId: activity.workflowRunId,
    workflowTool: activity.workflowTool,
    startedAtMs: now,
    expiresAtMs: now + LOCAL_WORKFLOW_ACTIVITY_HOLD_MS
  };
}

export function resetKernelUiPreservingCursor(state: AppState): void {
  const currentCursor = state.kernelUi.cursor;
  state.kernelUi = {
    ...createInitialKernelUiState(),
    cursor: currentCursor
  };
}

export function syncKernelUiToManagerState(state: AppState): void {
  const manager = state.health?.pipeline_manager;
  if (manager?.available && !manager.active_recovery_event && isCompletedKernelMirror(state.kernelUi.latestMirrorEvent)) {
    state.kernelUi.activeRecoveryEvent = null;
  }
  const hasLocalBlockingUi = Boolean(state.kernelUi.activeDialog || state.kernelUi.activeRecoveryEvent || hasLocalKernelSurface(state));
  if (!manager?.available) {
    if (!hasLocalBlockingUi) resetKernelUiPreservingCursor(state);
    return;
  }
  const hasLiveKernelSurface = Boolean(
    manager.active_workflow_run
    || manager.active_pipeline_run
    || manager.active_dialog
    || manager.active_recovery_event
    || Number(manager.pending_kernel_event_count || 0) > 0
    || hasLocalBlockingUi
  );
  if (!hasLiveKernelSurface) resetKernelUiPreservingCursor(state);
}

export function isPipelineStartupStatus(manager: AppState["pipelineManager"] | null | undefined): boolean {
  const status = manager as (AppState["pipelineManager"] & { startup_pending?: boolean }) | null | undefined;
  const reason = String(status?.reason || "");
  return Boolean(status?.startup_pending)
    || /Taxonomy Agent is starting|Taxonomy Agent is still starting|Taxonomy Agent status is still loading|Taxonomy Agent startet noch|Taxonomy Agent Status wird noch geladen|Pipeline Manager startet noch|Pipeline Manager Status wird noch geladen/i.test(reason);
}

function isCompletedKernelMirror(mirrorEvent: { event_type?: string } | null): boolean {
  return String(mirrorEvent?.event_type || "") === "workflow_completed";
}
