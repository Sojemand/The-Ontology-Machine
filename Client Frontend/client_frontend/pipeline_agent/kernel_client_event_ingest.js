import {
  allowedEventScopedRecoveryTools,
  clientRequestId
} from "./kernel_recovery_scope.js";
import { RETIRED_RECOVERY_TOOL_AVAILABILITY_STATUSES } from "./kernel_status_policy.js";
import { HOST_ONLY_TOOL_NAMES } from "./kernel_tool_surface.js";
import { PipelineKernelAdapterRecoveryState } from "./kernel_client_recovery_state.js";

export class PipelineKernelAdapterEventIngest extends PipelineKernelAdapterRecoveryState {
  ingestKernelResponse(response) {
    if (!response || typeof response !== "object") return response;
    if (response.tool_name === "kernel_status") {
      this.latestKernelStatus = response.active_state || null;
    }
    if (response.tool_name === "kernel_resume_state") {
      this.latestResumeState = response.resume_state || null;
    }
    if (response.mirror_event && typeof response.mirror_event === "object") {
      this.ingestMirrorEvent(response.mirror_event);
    }
    if (response.progress_event && typeof response.progress_event === "object") {
      this.ingestProgressEvent(response.progress_event);
    }
    return response;
  }

  ingestKernelEventBatch(batch) {
    const responseBatch = batch && typeof batch === "object" ? batch : {};
    if (typeof responseBatch.cursor === "string") this.eventCursor = responseBatch.cursor;
    for (const event of Array.isArray(responseBatch.events) ? responseBatch.events : []) {
      const kind = String(event?.frontend_event_kind || "");
      if (kind === "interaction_request" && event.interaction_request) {
        this.activeDialog = {
          interaction_request: event.interaction_request,
          status: "active",
          mirror_event_id: String(event.mirror_event_id || event.interaction_request.mirror_event_id || "")
        };
      }
      if (kind === "interaction_resolved") {
        const currentRequestId = String(this.activeDialog?.interaction_request?.interaction_request_id || "");
        const resolvedRequestId = String(event?.interaction_request?.interaction_request_id || "");
        if (!resolvedRequestId || resolvedRequestId === currentRequestId) {
          this.activeDialog = null;
        }
      }
      if (kind === "progress_event" && event.progress_event) {
        this.ingestProgressEvent(event.progress_event);
      }
      if (kind === "mirror_event" && event.mirror_event) {
        this.ingestMirrorEvent(event.mirror_event);
      }
      if (kind === "tool_availability" && event.tool_availability) {
        const mirrorEventId = String(event.tool_availability.mirror_event_id || "");
        const mirrorEvent = this.mirrorEvents.get(mirrorEventId);
        if (mirrorEvent) {
          const status = String(event.tool_availability.status || "");
          if (RETIRED_RECOVERY_TOOL_AVAILABILITY_STATUSES.has(status)) {
            this.retireRecoveryMirrorEvent(mirrorEventId);
            continue;
          }
          mirrorEvent.allowed_agent_tools = Array.isArray(event.tool_availability.allowed_agent_tools)
            ? event.tool_availability.allowed_agent_tools.map((name) => String(name))
            : [];
          if (!allowedEventScopedRecoveryTools(mirrorEvent).length) {
            this.eventScopedTools = [];
            continue;
          }
          this.promoteRecoveryMirrorEvent(mirrorEvent);
        }
      }
    }
    return responseBatch;
  }

  drainKernelMirrorEvents() {
    const drained = [...this.pendingMirrorEvents];
    this.pendingMirrorEvents = [];
    return drained;
  }

  drainPendingAutoCallMirrorEvents() {
    const drained = [...this.pendingAutoCallMirrorEvents];
    this.pendingAutoCallMirrorEvents = [];
    return drained;
  }

  async listKernelEvents(cursor = "", callContext = {}) {
    const request = {
      schema_version: "semantic_control_kernel.client_events_request.v1",
      cursor: String(cursor || ""),
      limit: 50,
      host_surface_identity: "client_frontend_http_pipeline_session",
      client_instance_id: this.clientInstanceId,
      client_request_id: clientRequestId(callContext, "kernel-events")
    };
    const batch = await this.callKernelTool(HOST_ONLY_TOOL_NAMES.listEvents, request);
    return this.ingestKernelEventBatch(batch);
  }

  async submitInteractionResponse(interactionRequestId, responsePayload, callContext = {}) {
    const response = await this.callKernelTool(HOST_ONLY_TOOL_NAMES.submitInteraction, {
      schema_version: "semantic_control_kernel.interaction_response_submit.v1",
      interaction_request_id: String(interactionRequestId || responsePayload?.interaction_request_id || ""),
      response: responsePayload,
      target_identity: responsePayload?.target_identity || {},
      state_snapshot_identity: responsePayload?.state_snapshot_identity || {},
      host_surface_identity: "client_frontend_http_pipeline_session",
      client_request_id: clientRequestId(callContext, "interaction-submit")
    });
    this.applyInteractionBridgeResponse(response);
    return {
      bridge_response: response,
      // Rebuild from a fresh snapshot because a submitted dialog can replace one
      // pending request with a different one, which invalidates positional cursors.
      event_batch: await this.listKernelEvents("", callContext)
    };
  }

  async cancelInteraction(interactionRequestId, responsePayload, callContext = {}) {
    const response = await this.callKernelTool(HOST_ONLY_TOOL_NAMES.cancelInteraction, {
      schema_version: "semantic_control_kernel.interaction_cancel_request.v1",
      interaction_request_id: String(interactionRequestId || responsePayload?.interaction_request_id || ""),
      response_status: String(responsePayload?.response_status || "cancelled"),
      target_identity: responsePayload?.target_identity || {},
      state_snapshot_identity: responsePayload?.state_snapshot_identity || {},
      host_surface_identity: "client_frontend_http_pipeline_session",
      client_request_id: clientRequestId(callContext, "interaction-cancel"),
      cancellation_reason: String(responsePayload?.cancellation_reason || "user_cancelled")
    });
    this.applyInteractionBridgeResponse(response);
    return {
      bridge_response: response,
      // Cancellation can also rotate the active dialog set, so re-sync from the
      // current Kernel snapshot instead of continuing from the previous cursor.
      event_batch: await this.listKernelEvents("", callContext)
    };
  }
}
