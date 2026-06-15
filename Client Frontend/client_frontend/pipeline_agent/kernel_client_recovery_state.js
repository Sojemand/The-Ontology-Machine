import {
  RECOVERY_EVENT_TYPES,
  allowedEventScopedRecoveryTools,
  isRecoveryMirrorEvent
} from "./kernel_recovery_scope.js";
import {
  TERMINAL_PROGRESS_STATUSES,
  TERMINAL_WORKFLOW_MIRROR_EVENT_TYPES
} from "./kernel_status_policy.js";
import { shouldRetireRecoveryTools } from "./kernel_client_recovery_retirement.js";

export class PipelineKernelAdapterRecoveryState {
  activeRecoveryMirrorEvent() {
    return this.activeRecoveryMirrorEventId ? this.mirrorEvents.get(this.activeRecoveryMirrorEventId) || null : null;
  }

  latestMirrorEvent() {
    let latest = null;
    for (const event of this.mirrorEvents.values()) {
      latest = event;
    }
    return latest;
  }

  activeEventScopedToolDefinitions() {
    return [...this.eventScopedTools];
  }

  resetVolatileState() {
    this.mirrorEvents = new Map();
    this.pendingMirrorEvents = [];
    this.pendingAutoCallMirrorEvents = [];
    this.activeDialog = null;
    this.activeRecoveryMirrorEventId = "";
    this.activeRecoveryEventByRecoveryId = new Map();
    this.eventCursor = "";
    this.latestKernelStatus = null;
    this.latestResumeState = null;
    this.latestProgressByWorkflowRun = new Map();
    this.terminalWorkflowRunIds = new Set();
    this.transientActiveWorkflowRun = null;
    this.eventScopedTools = [];
    this.eventScopedToolsWarning = "";
  }

  ingestMirrorEvent(mirrorEvent) {
    const normalized = mirrorEvent && typeof mirrorEvent === "object" ? { ...mirrorEvent } : null;
    const mirrorEventId = String(normalized?.mirror_event_id || "");
    if (!mirrorEventId) return;
    const existing = this.mirrorEvents.get(mirrorEventId);
    this.mirrorEvents.set(mirrorEventId, existing ? { ...existing, ...normalized } : normalized);
    if (!existing) {
      this.pendingMirrorEvents.push(this.mirrorEvents.get(mirrorEventId));
      if (normalized.is_kernel_auto_call === true) {
        this.pendingAutoCallMirrorEvents.push(this.mirrorEvents.get(mirrorEventId));
      }
    }
    if (normalized.progress_event && typeof normalized.progress_event === "object") {
      this.ingestProgressEvent(normalized.progress_event);
    }
    this.retireTerminalWorkflowMirrorEvent(this.mirrorEvents.get(mirrorEventId));
    this.promoteRecoveryMirrorEvent(this.mirrorEvents.get(mirrorEventId));
  }

  retireTerminalWorkflowMirrorEvent(mirrorEvent) {
    const eventType = String(mirrorEvent?.event_type || "");
    if (!TERMINAL_WORKFLOW_MIRROR_EVENT_TYPES.has(eventType)) return;
    const workflowRunId = String(mirrorEvent?.workflow_run_id || "");
    if (workflowRunId) {
      this.terminalWorkflowRunIds.add(workflowRunId);
      this.latestProgressByWorkflowRun.delete(workflowRunId);
    }
    if (workflowRunId && this.activeDialog?.interaction_request?.workflow_run_id === workflowRunId) {
      this.activeDialog = null;
    }
    if (
      (workflowRunId && String(this.transientActiveWorkflowRun?.workflow_run_id || "") === workflowRunId)
      || String(this.transientActiveWorkflowRun?.workflow_tool || "") === String(mirrorEvent?.workflow_tool || "")
    ) {
      this.transientActiveWorkflowRun = null;
    }
    if (eventType === "workflow_completed") {
      this.retireCompletedWorkflowRecovery(mirrorEvent);
    }
  }

  retireCompletedWorkflowRecovery(completedMirrorEvent) {
    const activeMirrorEvent = this.activeRecoveryMirrorEvent();
    if (activeMirrorEvent) {
      this.retireRecoveryMirrorEvent(String(activeMirrorEvent?.mirror_event_id || ""));
    }
    this.activeRecoveryEventByRecoveryId.clear();
    this.pendingMirrorEvents = this.pendingMirrorEvents.filter((event) => {
      return !isRecoveryMirrorEvent(event);
    });
    this.pendingAutoCallMirrorEvents = this.pendingAutoCallMirrorEvents.filter((event) => {
      return !isRecoveryMirrorEvent(event);
    });
  }

  promoteRecoveryMirrorEvent(mirrorEvent) {
    if (!mirrorEvent || typeof mirrorEvent !== "object") return;
    const recoveryEventId = String(mirrorEvent.recovery_event_id || "");
    const hasRecoveryTools = allowedEventScopedRecoveryTools(mirrorEvent).length > 0;
    const hasRecoveryContext = recoveryEventId || RECOVERY_EVENT_TYPES.has(String(mirrorEvent.event_type || ""));
    if (!hasRecoveryContext && !hasRecoveryTools) return;
    if (!recoveryEventId) {
      this.activeRecoveryMirrorEventId = String(mirrorEvent.mirror_event_id || "");
      return;
    }
    const previous = this.activeRecoveryEventByRecoveryId.get(recoveryEventId);
    this.activeRecoveryEventByRecoveryId.set(recoveryEventId, String(mirrorEvent.mirror_event_id || ""));
    this.activeRecoveryMirrorEventId = String(mirrorEvent.mirror_event_id || "");
    if (previous && previous !== this.activeRecoveryMirrorEventId) {
      this.eventScopedTools = [];
    }
  }

  retireRecoveryMirrorEvent(mirrorEventId) {
    const currentMirrorId = String(mirrorEventId || "");
    if (currentMirrorId && currentMirrorId === this.activeRecoveryMirrorEventId) {
      this.activeRecoveryMirrorEventId = "";
      this.eventScopedTools = [];
      this.eventScopedToolsWarning = "";
    }
  }

  ingestProgressEvent(progressEvent) {
    const workflowRunId = String(progressEvent?.workflow_run_id || "");
    if (!workflowRunId) return;
    const status = String(progressEvent?.status || "");
    if (this.terminalWorkflowRunIds.has(workflowRunId) && !TERMINAL_PROGRESS_STATUSES.has(status)) {
      return;
    }
    this.transientActiveWorkflowRun = null;
    const current = this.latestProgressByWorkflowRun.get(workflowRunId);
    const nextSequence = Number(progressEvent?.sequence_index || 0);
    const currentSequence = Number(current?.sequence_index || 0);
    if (!current || nextSequence >= currentSequence) {
      this.latestProgressByWorkflowRun.set(workflowRunId, { ...progressEvent });
    }
    if (TERMINAL_PROGRESS_STATUSES.has(status)) {
      this.terminalWorkflowRunIds.add(workflowRunId);
      if (this.activeDialog?.interaction_request?.workflow_run_id === workflowRunId) {
        this.activeDialog = null;
      }
    }
  }

  lastProgressEvent() {
    let latest = null;
    for (const event of this.latestProgressByWorkflowRun.values()) {
      if (!latest || Number(event.sequence_index || 0) >= Number(latest.sequence_index || 0)) {
        latest = event;
      }
    }
    return latest;
  }

  activeTransientWorkflowRun() {
    if (!this.transientActiveWorkflowRun) return null;
    if (Number(this.transientActiveWorkflowRun.expires_at_ms || 0) <= Date.now()) {
      this.transientActiveWorkflowRun = null;
      return null;
    }
    const { expires_at_ms: _expiresAtMs, ...summary } = this.transientActiveWorkflowRun;
    return summary;
  }

  clearTransientWorkflowRun(toolName = "") {
    if (!this.transientActiveWorkflowRun) return;
    if (!toolName || String(this.transientActiveWorkflowRun.workflow_tool || "") === String(toolName || "")) {
      this.transientActiveWorkflowRun = null;
    }
  }

  applyInteractionBridgeResponse(response) {
    const status = String(response?.status || "");
    if (status === "accepted" || status === "cancelled" || status === "closed") {
      this.activeDialog = null;
      return;
    }
    if (status === "rejected_stale" && this.activeDialog) {
      this.activeDialog = { ...this.activeDialog, status: "stale" };
    }
  }

  maybeRetireRecoveryTools(mirrorEvent, response) {
    if (shouldRetireRecoveryTools(response)) {
      const currentMirrorId = String(mirrorEvent?.mirror_event_id || "");
      if (currentMirrorId && currentMirrorId === this.activeRecoveryMirrorEventId) {
        this.activeRecoveryMirrorEventId = "";
        this.eventScopedTools = [];
      }
    }
  }
}
