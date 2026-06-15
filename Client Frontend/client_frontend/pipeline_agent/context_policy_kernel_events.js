import {
  TERMINAL_KERNEL_MIRROR_EVENT_TYPES,
  TERMINAL_PROGRESS_STATUSES,
  TRANSIENT_KERNEL_MIRROR_EVENT_TYPES
} from "./context_policy_constants.js";
import { clipMiddle } from "./context_policy_core.js";
import { compactLargeJson } from "./context_policy_json.js";

export function compactKernelMirrorEvent(mirrorEvent) {
  const source = mirrorEvent && typeof mirrorEvent === "object" ? mirrorEvent : {};
  const compact = {
    schema_version: String(source.schema_version || "kernel.mirror_event.v1"),
    mirror_event_id: String(source.mirror_event_id || ""),
    mirror_source: String(source.mirror_source || "kernel"),
    is_kernel_auto_call: Boolean(source.is_kernel_auto_call),
    event_type: String(source.event_type || ""),
    severity: String(source.severity || ""),
    user_visible_summary: clipMiddle(String(source.user_visible_summary || ""), 2_000)
  };
  if (source.current_state_summary) compact.current_state_summary = clipMiddle(String(source.current_state_summary), 2_000);
  if (source.workflow_run_id) compact.workflow_run_id = String(source.workflow_run_id);
  if (source.workflow_tool) compact.workflow_tool = String(source.workflow_tool);
  if (source.user_visible_cause) compact.user_visible_cause = clipMiddle(String(source.user_visible_cause), 2_000);
  if (Array.isArray(source.recovery_options)) compact.recovery_options = compactLargeJson(source.recovery_options, 1);
  if (Array.isArray(source.allowed_agent_tools)) compact.allowed_agent_tools = source.allowed_agent_tools.map((name) => String(name));
  if (source.agent_explanation_guidance != null) compact.agent_explanation_guidance = compactLargeJson(source.agent_explanation_guidance, 1);
  if (source.progress_event && typeof source.progress_event === "object") compact.progress_event = compactProgressEvent(source.progress_event);
  if (source.support_bundle_ref != null) compact.support_bundle_ref = compactLargeJson(source.support_bundle_ref, 1);
  if (source.technical_detail_ref != null) compact.technical_detail_ref = compactLargeJson(source.technical_detail_ref, 1);
  if (source.recovery_event_id) compact.recovery_event_id = String(source.recovery_event_id);
  if (source.kernel_dialog_state != null) compact.kernel_dialog_state = compactLargeJson(source.kernel_dialog_state, 1);
  return compact;
}

export function mergeKernelMirrorEventsIntoHistory(history, mirrorEvents) {
  const nextHistory = Array.isArray(history) ? history.map((entry) => ({ ...entry })) : [];
  const indexed = indexKernelMirrorHistory(nextHistory);
  for (const mirrorEvent of Array.isArray(mirrorEvents) ? mirrorEvents : []) {
    const compact = compactKernelMirrorEvent(mirrorEvent);
    if (!compact.mirror_event_id) continue;
    const entry = { role: "kernel", content: JSON.stringify(compact), kernel_mirror_event: compact };
    if (indexed.has(compact.mirror_event_id)) {
      nextHistory[indexed.get(compact.mirror_event_id)] = entry;
      continue;
    }
    indexed.set(compact.mirror_event_id, nextHistory.length);
    nextHistory.push(entry);
  }
  return nextHistory;
}

export function filterKernelHistoryForActiveState(history, activeState = {}) {
  const activeRunIds = activeWorkflowRunIdsFromState(activeState);
  const hasLiveWorkflowSurface = activeWorkflowRunCountFromState(activeState, activeRunIds) > 0
    || pendingInteractionCountFromState(activeState) > 0;
  return (Array.isArray(history) ? history : []).filter((entry) => {
    if (entry?.role !== "kernel") return true;
    const mirrorEvent = historyEntryMirrorEvent(entry);
    if (!isTransientWorkflowMirrorEvent(mirrorEvent)) return true;
    if (!hasLiveWorkflowSurface) return false;
    const workflowRunId = String(mirrorEvent?.workflow_run_id || mirrorEvent?.progress_event?.workflow_run_id || "");
    if (!workflowRunId || activeRunIds.size === 0) return true;
    return activeRunIds.has(workflowRunId);
  });
}

export function historyEntryMirrorEvent(entry) {
  if (entry?.kernel_mirror_event && typeof entry.kernel_mirror_event === "object") return entry.kernel_mirror_event;
  try {
    const parsed = JSON.parse(String(entry?.content || "{}"));
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function compactProgressEvent(progressEvent) {
  return compactLargeJson({
    workflow_run_id: progressEvent.workflow_run_id,
    workflow_tool: progressEvent.workflow_tool,
    step_id: progressEvent.step_id,
    step_label: progressEvent.step_label,
    status: progressEvent.status,
    user_visible_summary: progressEvent.user_visible_summary,
    timestamp: progressEvent.timestamp
  }, 1);
}

function indexKernelMirrorHistory(history) {
  const indexed = new Map();
  history.forEach((entry, index) => {
    if (entry?.role === "kernel" && entry?.kernel_mirror_event?.mirror_event_id) {
      indexed.set(String(entry.kernel_mirror_event.mirror_event_id), index);
    }
  });
  return indexed;
}

function activeWorkflowRunIdsFromState(activeState = {}) {
  const runs = Array.isArray(activeState?.active_workflow_runs) ? activeState.active_workflow_runs : [];
  return new Set(runs.map((run) => String(run?.workflow_run_id || run?.run_id || "")).filter(Boolean));
}

function activeWorkflowRunCountFromState(activeState = {}, activeRunIds = activeWorkflowRunIdsFromState(activeState)) {
  const explicit = Number(activeState?.active_workflow_run_count);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  return activeRunIds.size;
}

function pendingInteractionCountFromState(activeState = {}) {
  const explicit = Number(activeState?.pending_interaction_count);
  return Number.isFinite(explicit) && explicit > 0 ? explicit : 0;
}

function isTransientWorkflowMirrorEvent(mirrorEvent) {
  if (!mirrorEvent || typeof mirrorEvent !== "object") return false;
  const eventType = String(mirrorEvent.event_type || "");
  if (TERMINAL_KERNEL_MIRROR_EVENT_TYPES.has(eventType)) return false;
  const progressStatus = String(mirrorEvent?.progress_event?.status || "");
  if (TERMINAL_PROGRESS_STATUSES.has(progressStatus)) return false;
  if (mirrorEvent.kernel_dialog_state) return true;
  if (progressStatus && !TERMINAL_PROGRESS_STATUSES.has(progressStatus)) return true;
  if (eventType === "progress") return false;
  return TRANSIENT_KERNEL_MIRROR_EVENT_TYPES.has(eventType);
}
