export const TERMINAL_PROGRESS_STATUSES = new Set(["completed", "cancelled", "failed"]);
export const TERMINAL_WORKFLOW_MIRROR_EVENT_TYPES = new Set(["workflow_completed", "workflow_cancelled", "workflow_failed"]);
export const RETIRED_RECOVERY_TOOL_AVAILABILITY_STATUSES = new Set(["resolved", "cancelled", "expired", "superseded", "stale"]);

const TRANSIENT_WORKFLOW_SUMMARY_TTL_MS = 15000;

export function buildTransientWorkflowRunSummary(toolName) {
  const now = Date.now();
  return {
    workflow_run_id: `client_pending_${Math.random().toString(16).slice(2, 10)}`,
    workflow_tool: String(toolName || ""),
    status: "step_started",
    step_id: "client_frontend_handoff",
    step_label: "Workflow handoff",
    user_visible_summary: "Workflow wurde an den Kernel uebergeben. Warte auf den ersten Kernel-Fortschritt.",
    updated_at: new Date(now).toISOString(),
    transient: true,
    expires_at_ms: now + TRANSIENT_WORKFLOW_SUMMARY_TTL_MS
  };
}

export function activeWorkflowRunIdsFromState(activeState = {}) {
  const runs = Array.isArray(activeState?.active_workflow_runs) ? activeState.active_workflow_runs : [];
  return new Set(
    runs
      .map((run) => String(run?.workflow_run_id || run?.run_id || ""))
      .filter(Boolean)
  );
}

export function activeWorkflowRunCountFromState(activeState = {}, activeWorkflowRunIds = activeWorkflowRunIdsFromState(activeState)) {
  const explicit = Number(activeState?.active_workflow_run_count);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  return activeWorkflowRunIds.size;
}

export function pendingInteractionCountFromState(activeState = {}) {
  const explicit = Number(activeState?.pending_interaction_count);
  return Number.isFinite(explicit) && explicit > 0 ? explicit : 0;
}

export function hasPendingInteractionCount(activeState = {}) {
  return Object.prototype.hasOwnProperty.call(activeState || {}, "pending_interaction_count");
}

export function hasAuthoritativeActiveState(activeState = {}) {
  const source = activeState && typeof activeState === "object" ? activeState : {};
  return Array.isArray(source.active_workflow_runs)
    || Object.prototype.hasOwnProperty.call(source, "active_workflow_run_count")
    || Object.prototype.hasOwnProperty.call(source, "pending_interaction_count");
}

export function isTransientWorkflowMirrorEvent(mirrorEvent) {
  if (!mirrorEvent || typeof mirrorEvent !== "object") return false;
  const eventType = String(mirrorEvent.event_type || "");
  if (TERMINAL_WORKFLOW_MIRROR_EVENT_TYPES.has(eventType)) {
    return false;
  }
  const progressStatus = String(mirrorEvent?.progress_event?.status || "");
  if (TERMINAL_PROGRESS_STATUSES.has(progressStatus)) return false;
  if (mirrorEvent.kernel_dialog_state) return true;
  if (progressStatus && !TERMINAL_PROGRESS_STATUSES.has(progressStatus)) return true;
  if (eventType === "progress") return false;
  return eventType === "input_dialog_opened"
    || eventType === "selection_dialog_opened"
    || eventType === "confirmation_dialog_opened";
}

export function shouldExposeActiveDialog(activeDialog, {
  activeWorkflowRuns = [],
  activeWorkflowRunCount = 0,
  progressEvent = null,
  pendingKernelEventCount = 0,
  pendingInteractionCount = 0,
  activeStateAuthoritative = false
} = {}) {
  if (!activeDialog || typeof activeDialog !== "object") return false;
  const dialogWorkflowRunId = String(activeDialog?.interaction_request?.workflow_run_id || "");
  const activeWorkflowRunIds = new Set(
    (Array.isArray(activeWorkflowRuns) ? activeWorkflowRuns : [])
      .map((run) => String(run?.workflow_run_id || run?.run_id || ""))
      .filter(Boolean)
  );
  if (activeWorkflowRunIds.size > 0) return !dialogWorkflowRunId || activeWorkflowRunIds.has(dialogWorkflowRunId);
  if (Number(activeWorkflowRunCount || 0) > 0) return true;
  if (Number(pendingInteractionCount || 0) > 0) return true;
  if (!activeStateAuthoritative && Number(pendingKernelEventCount || 0) > 0) return true;
  if (!progressEvent || typeof progressEvent !== "object") return false;
  return String(progressEvent.status || "") === "waiting_for_user"
    && String(progressEvent.workflow_run_id || "") === String(activeDialog?.interaction_request?.workflow_run_id || "");
}

export function shouldExposeProgressFallback(progressEvent, { activeDialog = null, activeRecoveryEvent = null, pendingKernelEventCount = 0 } = {}) {
  if (!progressEvent || typeof progressEvent !== "object") return false;
  const status = String(progressEvent.status || "");
  if (TERMINAL_PROGRESS_STATUSES.has(status)) return false;
  if (status === "step_completed") return false;
  if (status === "waiting_for_user") return Boolean(activeDialog);
  if (status === "blocked") return Boolean(activeRecoveryEvent) || Number(pendingKernelEventCount || 0) > 0;
  return true;
}
