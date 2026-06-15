import { cleanObject } from "./kernel_object_utils.js";
import { EVENT_SCOPED_RECOVERY_TOOL_NAMES } from "./kernel_tool_surface.js";

export const RECOVERY_EVENT_TYPES = new Set([
  "recovery_state",
  "validation_error",
  "pipeline_error",
  "llm_validation_retry",
  "llm_validation_failed_final",
  "workflow_cancelled"
]);

export function buildEventScopedToolArguments(name, mirrorEvent, callContext = {}) {
  const recoveryScope = buildRecoveryScopeForTool(name, mirrorEvent);
  if (!recoveryScope) return null;
  return cleanObject({
    ...recoveryScope,
    mirror_event_id: String(mirrorEvent?.mirror_event_id || ""),
    recovery_event_id: String(mirrorEvent?.recovery_event_id || ""),
    state_snapshot_id: stateSnapshotId(mirrorEvent),
    client_request_id: clientRequestId(callContext, "event-scoped-tool"),
    tool_call_nonce: toolCallNonce(callContext),
    conversation_ref: String(callContext.conversationRef || ""),
    turn_ref: String(callContext.turnRef || "")
  });
}

export function clientRequestId(callContext = {}, prefix = "client") {
  const explicit = String(callContext.clientRequestId || "").trim();
  if (explicit) return explicit;
  return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
}

function toolCallNonce(callContext = {}) {
  const explicit = String(callContext.toolCallNonce || "").trim();
  if (explicit) return explicit;
  return `nonce-${Math.random().toString(16).slice(2, 14)}`;
}

export function definitionsMatchMirrorEvent(mirrorEvent) {
  if (!Array.isArray(mirrorEvent?.allowed_agent_tool_definitions) || !mirrorEvent.allowed_agent_tool_definitions.length) {
    return false;
  }
  const definitionNames = mirrorEvent.allowed_agent_tool_definitions.map((tool) => String(tool?.name || ""));
  const allowedRecoveryTools = allowedEventScopedRecoveryTools(mirrorEvent);
  if (!allowedRecoveryTools.length || definitionNames.length !== allowedRecoveryTools.length) return false;
  if (new Set(definitionNames).size !== definitionNames.length) return false;
  return allowedRecoveryTools.every((name) => definitionNames.includes(name))
    && definitionNames.every((name) => allowedRecoveryTools.includes(name));
}

function allowedAgentTools(mirrorEvent) {
  return Array.isArray(mirrorEvent?.allowed_agent_tools) ? mirrorEvent.allowed_agent_tools.map((name) => String(name)) : [];
}

export function candidateEventScopedRecoveryTools(mirrorEvent) {
  return allowedAgentTools(mirrorEvent).filter((name) => EVENT_SCOPED_RECOVERY_TOOL_NAMES.includes(name));
}

export function allowedEventScopedRecoveryTools(mirrorEvent) {
  return candidateEventScopedRecoveryTools(mirrorEvent).filter((name) => Boolean(buildRecoveryScopeForTool(name, mirrorEvent)));
}

export function isRecoveryMirrorEvent(mirrorEvent) {
  if (!mirrorEvent || typeof mirrorEvent !== "object") return false;
  return Boolean(String(mirrorEvent.recovery_event_id || ""))
    || RECOVERY_EVENT_TYPES.has(String(mirrorEvent.event_type || ""))
    || allowedEventScopedRecoveryTools(mirrorEvent).length > 0;
}

function buildRecoveryScopeForTool(name, mirrorEvent) {
  const option = recoveryOptionForTool(mirrorEvent, name);
  const base = cleanObject({
    recovery_id: String(option?.recovery_id || ""),
    recovery_event_id: String(option?.recovery_event_id || mirrorEvent?.recovery_event_id || ""),
    state_snapshot_id: stateSnapshotId(mirrorEvent)
  });
  if (!base.recovery_id || !base.recovery_event_id || !base.state_snapshot_id) return null;
  if (name === "kernel_retry_recoverable_workflow") {
    const workflowRunId = String(mirrorEvent?.workflow_run_id || option?.workflow_run_id || "");
    return workflowRunId ? { ...base, workflow_run_id: workflowRunId } : null;
  }
  if (name === "kernel_resolve_stale_lock") {
    const lockId = stringFromOption(option, "lock_id");
    return lockId ? { ...base, lock_id: lockId } : null;
  }
  if (name === "kernel_rebind_database_artifact_tree") {
    const bindingRecoveryId = stringFromOption(option, "binding_recovery_id");
    return bindingRecoveryId ? { ...base, binding_recovery_id: bindingRecoveryId } : null;
  }
  if (name === "kernel_discard_or_archive_staged_work") {
    const stagedWorkRef = stringFromOption(option, "staged_work_ref");
    return stagedWorkRef ? { ...base, staged_work_ref: stagedWorkRef } : null;
  }
  if (name === "kernel_reconcile_partial_pipeline_run") {
    const partialRunRef = stringFromOption(option, "partial_run_ref");
    return partialRunRef ? { ...base, partial_run_ref: partialRunRef } : null;
  }
  if (name === "kernel_open_support_bundle") {
    const supportBundleId = String(option?.support_bundle_ref?.support_bundle_id || mirrorEvent?.support_bundle_ref?.support_bundle_id || "");
    return supportBundleId ? { ...base, support_bundle_id: supportBundleId } : null;
  }
  return base;
}

function recoveryOptionForTool(mirrorEvent, name) {
  const options = Array.isArray(mirrorEvent?.recovery_options) ? mirrorEvent.recovery_options : [];
  return options.find((option) => option && typeof option === "object" && String(option.agent_tool || "") === name && String(option.recovery_id || ""));
}

function stringFromOption(option, fieldName) {
  return String(option?.[fieldName] || option?.target_identity?.[fieldName] || option?.state_snapshot_identity?.[fieldName] || "");
}

export function stateSnapshotId(mirrorEvent) {
  const candidate = mirrorEvent?.state_snapshot_id
    || mirrorEvent?.state_snapshot_identity?.state_snapshot_id
    || mirrorEvent?.kernel_dialog_state?.state_snapshot_id
    || mirrorEvent?.kernel_dialog_state?.state_snapshot_identity?.state_snapshot_id
    || "";
  return String(candidate);
}
