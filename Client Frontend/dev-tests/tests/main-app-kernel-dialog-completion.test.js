import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, deferred, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, interactionRequest, progressEvent } from "./pipeline-agent-test-fixtures.js";

test("submitting the final kernel dialog triggers the queued completion auto-reply and clears stale kernel UI", async () => {
  const request = interactionRequest({
    interaction_function: "name_database",
    interaction_kind: "input",
    dialog_type: "text_input",
    response_shape: "text_value",
    user_visible_title: "Name Database",
    user_visible_summary: "Enter the database name for Artifact Tree Kernel Test.",
    prefilled_values: { text_value: "Artifact Tree Kernel Test" }
  });
  let healthCallCount = 0;
  let kernelEventPollCount = 0;
  const { app, dom } = createAppHarness({
    getHealth: async () => {
      healthCallCount += 1;
      return health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 30,
          semantic_control_kernel_tool_count: 30,
          permission_status: null,
          permission_warning: "",
          active_workflow_run: healthCallCount === 1 ? {
            workflow_run_id: "wr_final_dialog",
            workflow_tool: "empty_database_no_semantic_release",
            status: "waiting_for_user",
            step_id: "dc_collect_target",
            step_label: "dc_collect_target",
            user_visible_summary: "Enter the database name for Artifact Tree Kernel Test."
          } : null,
          active_dialog: null,
          active_recovery_event: null,
          pending_kernel_event_count: 0
        }
      });
    },
    getPipelineKernelEvents: async () => {
      kernelEventPollCount += 1;
      if (kernelEventPollCount === 1) {
        return eventBatch([
          clientFrontendEvent("interaction_request", {
            interaction_request: request
          })
        ], "1");
      }
      return {
        ...eventBatch([], "2"),
        auto_results: [{
          answer: "Die leere Datenbank ist erstellt. Als Nächstes kannst du den Default-Release anhängen oder eine Custom-Taxonomie plus Projektionen bauen.",
          sources: [],
          mode: "analytic",
          exactness: "evidence_grounded",
          metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "kernel_auto_report"
        }]
      };
    },
    submitKernelInteractionResponse: async () => ({
      bridge_response: {
        schema_version: "semantic_control_kernel.host_bridge_response.v1",
        status: "accepted",
        user_visible_summary: "Interaction accepted."
      },
      event_batch: eventBatch([
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            workflow_run_id: "wr_final_dialog",
            workflow_tool: "empty_database_no_semantic_release",
            step_id: "dc_final_notice",
            step_label: "dc_final_notice",
            status: "completed",
            sequence_index: 15,
            user_visible_summary: "Artifact Tree and empty Corpus DB were created. No Semantic Release is attached yet."
          })
        })
      ], "2")
    })
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const input = dom.window.document.querySelector("#text-value");
  input.value = "Artifact Tree Kernel Test";
  dom.window.document.querySelector("#kernel-dialog-actions button")?.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(dom.window.document.querySelector("#messages")?.textContent || "", /leere datenbank ist erstellt/i);
  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);
  assert.match(dom.window.document.querySelector("#pipeline-progress-title")?.textContent || "", /completed/i);
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, true);
  assert.ok(kernelEventPollCount >= 2);
});

test("interaction route auto_results render the completion reply even when the next kernel poll is empty", async () => {
  const request = interactionRequest({
    interaction_function: "name_database",
    interaction_kind: "input",
    dialog_type: "text_input",
    response_shape: "text_value",
    user_visible_title: "Name Database",
    user_visible_summary: "Enter the database name for Artifact Tree Kernel Test.",
    prefilled_values: { text_value: "Artifact Tree Kernel Test" }
  });
  let healthCallCount = 0;
  let kernelEventPollCount = 0;
  const { app, dom } = createAppHarness({
    getHealth: async () => {
      healthCallCount += 1;
      return health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 30,
          semantic_control_kernel_tool_count: 30,
          permission_status: null,
          permission_warning: "",
          active_workflow_run: healthCallCount === 1 ? {
            workflow_run_id: "wr_final_dialog_auto_results",
            workflow_tool: "empty_database_no_semantic_release",
            status: "waiting_for_user",
            step_id: "dc_collect_target",
            step_label: "dc_collect_target",
            user_visible_summary: "Enter the database name for Artifact Tree Kernel Test."
          } : null,
          active_dialog: null,
          active_recovery_event: null,
          pending_kernel_event_count: 0
        }
      });
    },
    getPipelineKernelEvents: async () => {
      kernelEventPollCount += 1;
      if (kernelEventPollCount === 1) {
        return eventBatch([
          clientFrontendEvent("interaction_request", {
            interaction_request: request
          })
        ], "1");
      }
      return eventBatch([], String(kernelEventPollCount));
    },
    submitKernelInteractionResponse: async () => ({
      bridge_response: {
        schema_version: "semantic_control_kernel.host_bridge_response.v1",
        status: "accepted",
        user_visible_summary: "Interaction accepted."
      },
      event_batch: eventBatch([
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            workflow_run_id: "wr_final_dialog_auto_results",
            workflow_tool: "empty_database_no_semantic_release",
            step_id: "dc_final_notice",
            step_label: "dc_final_notice",
            status: "completed",
            sequence_index: 15,
            user_visible_summary: "Artifact Tree and empty Corpus DB were created. No Semantic Release is attached yet."
          })
        })
      ], "2"),
      auto_results: [{
        answer: "Die leere Datenbank ist erstellt. Als Naechstes kannst du den Default-Release anhaengen oder eine Custom-Taxonomie plus Projektionen bauen.",
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

  const input = dom.window.document.querySelector("#text-value");
  input.value = "Artifact Tree Kernel Test";
  dom.window.document.querySelector("#kernel-dialog-actions button")?.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));

  const messagesText = dom.window.document.querySelector("#messages")?.textContent || "";
  assert.match(messagesText, /leere datenbank ist erstellt/i);
  assert.equal((messagesText.match(/leere datenbank ist erstellt/ig) || []).length, 1);
  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);
  assert.match(dom.window.document.querySelector("#pipeline-progress-title")?.textContent || "", /completed/i);
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, true);
  assert.ok(kernelEventPollCount >= 2);
});
