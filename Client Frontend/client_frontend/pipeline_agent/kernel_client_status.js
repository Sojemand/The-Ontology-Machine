import {
  TERMINAL_PROGRESS_STATUSES,
  activeWorkflowRunCountFromState,
  activeWorkflowRunIdsFromState,
  hasAuthoritativeActiveState,
  hasPendingInteractionCount,
  isTransientWorkflowMirrorEvent,
  pendingInteractionCountFromState,
  shouldExposeActiveDialog,
  shouldExposeProgressFallback
} from "./kernel_status_policy.js";
import { PipelineKernelAdapterEventIngest } from "./kernel_client_event_ingest.js";

function progressSummary(progressEvent) {
  return {
    workflow_run_id: progressEvent.workflow_run_id,
    workflow_tool: progressEvent.workflow_tool,
    status: progressEvent.status,
    step_id: progressEvent.step_id,
    step_label: progressEvent.step_label,
    user_visible_summary: progressEvent.user_visible_summary
  };
}

export class PipelineKernelAdapterStatus extends PipelineKernelAdapterEventIngest {
  async status(callContext = {}) {
    const response = await this.callVisibleTool("kernel_status", {}, callContext);
    const activeState = response?.active_state && typeof response.active_state === "object" ? response.active_state : {};
    this.reconcileVolatileStateWithActiveState(activeState);
    return this.buildStatus(activeState);
  }

  cachedStatus() {
    const activeState = this.latestKernelStatus && typeof this.latestKernelStatus === "object" ? this.latestKernelStatus : {};
    return this.buildStatus(activeState);
  }

  reconcileVolatileStateWithActiveState(activeState = {}) {
    const activeWorkflowRunIds = activeWorkflowRunIdsFromState(activeState);
    const activeWorkflowRunCount = activeWorkflowRunCountFromState(activeState, activeWorkflowRunIds);
    const pendingInteractionCount = pendingInteractionCountFromState(activeState);
    if (hasPendingInteractionCount(activeState) && pendingInteractionCount <= 0) {
      this.activeDialog = null;
    }
    if (activeWorkflowRunCount > 0 || pendingInteractionCount > 0) {
      for (const workflowRunId of activeWorkflowRunIds) this.terminalWorkflowRunIds.delete(workflowRunId);
      if (activeWorkflowRunIds.size > 0) this.pruneInactiveProgress(activeWorkflowRunIds);
      return;
    }
    this.activeDialog = null;
    for (const [workflowRunId, progressEvent] of this.latestProgressByWorkflowRun.entries()) {
      if (!TERMINAL_PROGRESS_STATUSES.has(String(progressEvent?.status || ""))) {
        this.latestProgressByWorkflowRun.delete(workflowRunId);
      }
    }
    this.pendingMirrorEvents = this.pendingMirrorEvents.filter((event) => !isTransientWorkflowMirrorEvent(event));
    this.pendingAutoCallMirrorEvents = this.pendingAutoCallMirrorEvents.filter((event) => !isTransientWorkflowMirrorEvent(event));
  }

  pruneInactiveProgress(activeWorkflowRunIds) {
    if (!activeWorkflowRunIds?.size) return;
    for (const [workflowRunId, progressEvent] of this.latestProgressByWorkflowRun.entries()) {
      if (!activeWorkflowRunIds.has(String(workflowRunId)) && !TERMINAL_PROGRESS_STATUSES.has(String(progressEvent?.status || ""))) {
        this.latestProgressByWorkflowRun.delete(workflowRunId);
      }
    }
    const activeDialogWorkflowRunId = String(this.activeDialog?.interaction_request?.workflow_run_id || "");
    if (activeDialogWorkflowRunId && !activeWorkflowRunIds.has(activeDialogWorkflowRunId)) {
      this.activeDialog = null;
    }
  }

  buildStatus(activeState = {}) {
    const latestMirrorEvent = this.latestMirrorEvent();
    if (String(latestMirrorEvent?.event_type || "") === "workflow_completed") {
      this.retireCompletedWorkflowRecovery(latestMirrorEvent);
    }
    const activeWorkflowRuns = Array.isArray(activeState.active_workflow_runs) ? activeState.active_workflow_runs : [];
    const activeWorkflowRunCount = activeWorkflowRunCountFromState(activeState, activeWorkflowRunIdsFromState(activeState));
    const pendingInteractionCount = pendingInteractionCountFromState(activeState);
    const activeStateAuthoritative = hasAuthoritativeActiveState(activeState);
    const lastProgress = this.lastProgressEvent();
    const activeRecoveryEvent = this.activeRecoveryMirrorEvent();
    const transientActiveWorkflowRun = this.activeTransientWorkflowRun();
    const fallbackProgress = shouldExposeProgressFallback(lastProgress, {
      activeDialog: this.activeDialog,
      activeRecoveryEvent,
      pendingKernelEventCount: this.pendingMirrorEvents.length
    }) ? lastProgress : null;
    const fallbackActiveDialog = shouldExposeActiveDialog(this.activeDialog, {
      activeWorkflowRuns,
      activeWorkflowRunCount,
      progressEvent: fallbackProgress,
      pendingKernelEventCount: this.pendingMirrorEvents.length,
      pendingInteractionCount,
      activeStateAuthoritative
    }) ? this.activeDialog : null;
    return {
      available: true,
      reason: "",
      kernel_status: activeState,
      semantic_control_kernel_tool_count: this.permanentTools.length,
      active_workflow_run: activeWorkflowRuns[0] || (fallbackProgress ? progressSummary(fallbackProgress) : transientActiveWorkflowRun),
      active_pipeline_run: fallbackProgress && String(fallbackProgress.workflow_tool || "").includes("pipeline")
        ? progressSummary(fallbackProgress)
        : null,
      active_dialog: fallbackActiveDialog,
      active_recovery_event: activeRecoveryEvent,
      pending_kernel_event_count: this.pendingMirrorEvents.length,
      operational_warning: this.eventScopedToolsWarning
    };
  }
}
