import { isEmptyObject } from "./kernel_object_utils.js";
import {
  allowedEventScopedRecoveryTools,
  buildEventScopedToolArguments,
  candidateEventScopedRecoveryTools,
  clientRequestId,
  definitionsMatchMirrorEvent,
  stateSnapshotId
} from "./kernel_recovery_scope.js";
import { buildTransientWorkflowRunSummary } from "./kernel_status_policy.js";
import {
  isWorkflowStarterTool,
  normalizeKernelResponse,
  rejectedToolResult,
  toModelVisibleToolDefinition,
  visibleToolArguments
} from "./kernel_tool_surface.js";
import { PipelineKernelAdapterStatus } from "./kernel_client_status.js";

export class PipelineKernelAdapterTools extends PipelineKernelAdapterStatus {
  async resumeState(callContext = {}) {
    const response = await this.callVisibleTool("kernel_resume_state", {}, callContext);
    this.latestResumeState = response?.resume_state || null;
    return response;
  }

  async cancelActiveRun(callContext = {}) {
    return await this.callVisibleTool("kernel_cancel_active_run", {}, callContext);
  }

  async callVisibleTool(name, modelArguments = {}, callContext = {}) {
    if (!this.permanentToolMap.has(name)) {
      return rejectedToolResult(name, "unknown_kernel_tool", "The selected Kernel tool is not part of the permanent Taxonomy Agent surface.");
    }
    const argumentCheck = visibleToolArguments(name, modelArguments);
    if (!argumentCheck.ok) {
      return rejectedToolResult(name, "agent_authored_arguments_rejected", argumentCheck.message);
    }
    if (isWorkflowStarterTool(name)) {
      this.transientActiveWorkflowRun = buildTransientWorkflowRunSummary(name);
    }
    let response;
    try {
      response = normalizeKernelResponse(await this.callKernelTool(name, argumentCheck.arguments), name);
    } catch (error) {
      this.clearTransientWorkflowRun(name);
      throw error;
    }
    this.ingestKernelResponse(response);
    if (response.status === "rejected" || response.status === "failed") {
      this.clearTransientWorkflowRun(name);
    }
    return response;
  }

  async callEventScopedTool(name, modelArguments = {}, mirrorEvent = null, callContext = {}) {
    const activeMirrorEvent = mirrorEvent || this.activeRecoveryMirrorEvent();
    if (!activeMirrorEvent || !allowedEventScopedRecoveryTools(activeMirrorEvent).includes(name)) {
      return rejectedToolResult(name, "event_scoped_tool_not_available", "This recovery tool is not available for the current Kernel mirror event.");
    }
    if (!isEmptyObject(modelArguments)) {
      return rejectedToolResult(name, "agent_authored_arguments_rejected", "Kernel recovery tools do not accept model-authored arguments.");
    }
    const eventScopeArguments = buildEventScopedToolArguments(name, activeMirrorEvent, callContext);
    if (!eventScopeArguments) {
      return rejectedToolResult(name, "event_scoped_tool_not_available", "This recovery tool is not bound to a complete Kernel recovery option.");
    }
    const response = normalizeKernelResponse(await this.callKernelTool(name, eventScopeArguments), name);
    this.ingestKernelResponse(response);
    this.maybeRetireRecoveryTools(activeMirrorEvent, response);
    return response;
  }

  async prepareEventScopedTools(callContext = {}) {
    const mirrorEvent = this.activeRecoveryMirrorEvent();
    if (!mirrorEvent) {
      this.eventScopedTools = [];
      this.eventScopedToolsWarning = "";
      return this.toolDefinitions();
    }
    if (candidateEventScopedRecoveryTools(mirrorEvent).length && !allowedEventScopedRecoveryTools(mirrorEvent).length) {
      this.eventScopedTools = [];
      this.eventScopedToolsWarning = "event_scoped_recovery_scope_unbound";
      return this.toolDefinitions();
    }
    const allowedRecoveryTools = allowedEventScopedRecoveryTools(mirrorEvent);
    if (definitionsMatchMirrorEvent(mirrorEvent)) {
      this.eventScopedTools = mirrorEvent.allowed_agent_tool_definitions
        .filter((tool) => allowedRecoveryTools.includes(String(tool?.name || "")))
        .map((tool) => toModelVisibleToolDefinition(tool.name, tool));
      this.eventScopedToolsWarning = "";
      return this.toolDefinitions();
    }
    if (!allowedRecoveryTools.length) {
      this.eventScopedTools = [];
      this.eventScopedToolsWarning = "";
      return this.toolDefinitions();
    }
    return this.refreshEventScopedToolDefinitions(mirrorEvent, allowedRecoveryTools, callContext);
  }

  async refreshEventScopedToolDefinitions(mirrorEvent, allowedRecoveryTools, callContext = {}) {
    const response = await this.listEventScopedTools({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
      mirror_event_id: String(mirrorEvent.mirror_event_id || ""),
      recovery_event_id: String(mirrorEvent.recovery_event_id || ""),
      state_snapshot_id: stateSnapshotId(mirrorEvent),
      host_surface_identity: "client_frontend_pipeline_manager",
      client_request_id: clientRequestId(callContext, "event-scoped-tools")
    });
    if (response?.status !== "active") {
      this.eventScopedTools = [];
      this.eventScopedToolsWarning = "event_scoped_tool_definitions_unavailable";
      return this.toolDefinitions();
    }
    const visible = Array.isArray(response.tool_definitions) ? response.tool_definitions : [];
    const visibleNames = visible.map((tool) => String(tool?.name || ""));
    if (!allowedRecoveryTools.every((name) => visibleNames.includes(name))) {
      this.eventScopedTools = [];
      this.eventScopedToolsWarning = "event_scoped_tool_definitions_unavailable";
      return this.toolDefinitions();
    }
    this.eventScopedTools = visible
      .filter((tool) => allowedRecoveryTools.includes(String(tool?.name || "")))
      .map((tool) => toModelVisibleToolDefinition(String(tool?.name || ""), tool));
    this.eventScopedToolsWarning = "";
    return this.toolDefinitions();
  }
}
