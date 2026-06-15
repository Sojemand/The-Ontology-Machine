import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";
import {
  clientFrontendEvent,
  eventBatch,
  interactionRequest,
  mirrorEvent,
  progressEvent
} from "./pipeline-agent-test-fixtures.js";

test("go-live kernel event flow renders progress, final error, dialog and support notice without leaking recovery tools into chat", async () => {
  const supportDialog = interactionRequest({
    dialog_type: "support_bundle_notice",
    user_visible_title: "Support bundle available",
    user_visible_summary: "Kernel support evidence is ready."
  });
  const finalErrorMirror = mirrorEvent({
    mirror_event_id: "mev_final",
    recovery_event_id: "rev_final",
    is_kernel_auto_call: true,
    event_type: "llm_validation_failed_final",
    severity: "final_error",
    user_visible_summary: "The Kernel could not validate the LLM result after retries.",
    allowed_agent_tools: ["kernel_open_support_bundle"]
  });
  const { app, dom } = createAppHarness({
    getHealth: async () =>
      health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 30,
          semantic_control_kernel_tool_count: 30,
          permission_status: null,
          permission_warning: ""
        }
      }),
    getPipelineKernelEvents: async () =>
      eventBatch([
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            status: "waiting_for_user",
            user_visible_summary: "Waiting for the Kernel dialog."
          })
        }),
        clientFrontendEvent("mirror_event", { mirror_event: finalErrorMirror }),
        clientFrontendEvent("interaction_request", { interaction_request: supportDialog })
      ], "1")
  });

  await app.boot();
  await app.switchAgent("pipeline");

  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, false);
  assert.match(dom.window.document.querySelector("#pipeline-permission-status")?.textContent || "", /could not validate the llm result/i);
  assert.match(dom.window.document.querySelector("#kernel-dialog-summary")?.textContent || "", /support evidence/i);
  assert.doesNotMatch(dom.window.document.querySelector("#messages")?.textContent || "", /kernel_open_support_bundle/);
});

test("kernel auto results are appended into the active pipeline chat session", async () => {
  const reportText = "# Database Coverage Report\n\nCoverage is strong enough for the next review turn.";
  const { app, dom } = createAppHarness({
    getHealth: async () =>
      health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 30,
          semantic_control_kernel_tool_count: 30,
          permission_status: null,
          permission_warning: ""
        }
      }),
    getPipelineKernelEvents: async () => ({
      ...eventBatch([], "1"),
      auto_results: [{
        answer: reportText,
        sources: [],
        mode: "analytic",
        exactness: "evidence_grounded",
        metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
        ambiguities: [],
        method: "kernel_auto_report"
      }]
    })
  });

  await app.boot();
  await app.switchAgent("pipeline");

  assert.match(dom.window.document.querySelector("#messages")?.textContent || "", /Database Coverage Report/i);
  assert.match(dom.window.document.querySelector("#messages")?.textContent || "", /next review turn/i);
});

test("workflow completion with permanent next-step tools clears stale recovery chrome", async () => {
  const recoveryMirror = mirrorEvent({
    mirror_event_id: "mev_merge_recovery_ui",
    recovery_event_id: "rev_merge_recovery_ui",
    workflow_run_id: "wr_old_merge_ui",
    workflow_tool: "legacy_blocked_merge_route",
    event_type: "recovery_state",
    user_visible_summary: "Merge recovery required.",
    allowed_agent_tools: ["kernel_open_recovery_dialog"],
    recovery_options: [{ recovery_id: "rcv_merge_recovery_ui" }]
  });
  const completionMirror = mirrorEvent({
    mirror_event_id: "mev_merge_completion_ui",
    workflow_run_id: "wr_new_merge_ui",
    workflow_tool: "database_merge_additive_only",
    event_type: "workflow_completed",
    user_visible_summary: "Database merge is complete.",
    current_state_summary: "semantic_release_active",
    allowed_agent_tools: ["manual_pipeline_run", "database_modify_taxonomy", "database_modify_projections", "kernel_status"],
    recovery_options: []
  });
  const { app, dom } = createAppHarness({
    getHealth: async () =>
      health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 30,
          semantic_control_kernel_tool_count: 30,
          permission_status: null,
          permission_warning: ""
        }
      }),
    getPipelineKernelEvents: async () =>
      eventBatch([
        clientFrontendEvent("mirror_event", { mirror_event: recoveryMirror }),
        clientFrontendEvent("mirror_event", { mirror_event: completionMirror })
      ], "1")
  });

  await app.boot();
  await app.switchAgent("pipeline");

  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, true);
  assert.doesNotMatch(dom.window.document.querySelector("#pipeline-permission-status")?.textContent || "", /recovery/i);
});

test("kernel recovery status text is not recreated when runtime refresh keeps the same summary", async () => {
  const finalErrorMirror = mirrorEvent({
    mirror_event_id: "mev_final_stable",
    recovery_event_id: "rev_final_stable",
    is_kernel_auto_call: true,
    event_type: "llm_validation_failed_final",
    severity: "final_error",
    user_visible_summary: "The Kernel could not validate the structured LLM result after retries.",
    allowed_agent_tools: ["kernel_open_support_bundle"]
  });
  let kernelEventPollCount = 0;
  const { app, dom } = createAppHarness({
    getHealth: async () =>
      health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 30,
          semantic_control_kernel_tool_count: 30,
          permission_status: null,
          permission_warning: ""
        }
      }),
    getPipelineKernelEvents: async () => {
      kernelEventPollCount += 1;
      return kernelEventPollCount === 1
        ? eventBatch([
          clientFrontendEvent("mirror_event", {
            mirror_event: finalErrorMirror
          })
        ], String(kernelEventPollCount))
        : eventBatch([], String(kernelEventPollCount));
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const permissionStatus = dom.window.document.querySelector("#pipeline-permission-status");
  const originalTextNode = permissionStatus?.firstChild;

  await app.refreshRuntimeStatus();
  await app.refreshRuntimeStatus();

  assert.equal(permissionStatus?.firstChild, originalTextNode);
  assert.match(permissionStatus?.textContent || "", /structured llm result/i);
});
