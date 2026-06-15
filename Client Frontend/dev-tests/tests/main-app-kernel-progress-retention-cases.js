import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, progressEvent } from "./pipeline-agent-test-fixtures.js";

test("kernel progress ignores older events that arrive after a newer event for the same workflow", async () => {
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
            workflow_run_id: "wr_taxonomy",
            workflow_tool: "empty_database_custom_taxonomy_no_projections",
            step_id: "tax_analyze_samples",
            step_label: "tax_analyze_samples",
            status: "step_started",
            sequence_index: 21,
            user_visible_summary: "tax_analyze_samples started."
          })
        }),
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            workflow_run_id: "wr_taxonomy",
            workflow_tool: "empty_database_custom_taxonomy_no_projections",
            step_id: "tax_require_samples",
            step_label: "tax_require_samples",
            status: "waiting_for_user",
            sequence_index: 17,
            user_visible_summary: "Place the raw taxonomy sample files in the Artifact Tree Input folder."
          })
        })
      ], "2")
  });

  await app.boot();
  await app.switchAgent("pipeline");

  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);
  assert.equal(dom.window.document.querySelector("#pipeline-progress-title")?.textContent, "Kernel step running");
  assert.match(dom.window.document.querySelector("#pipeline-progress-summary")?.textContent || "", /tax_analyze_samples started/i);
});

test("health polling keeps retained kernel progress visible without an active manager snapshot", async () => {
  let eventCalls = 0;
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
      eventCalls += 1;
      if (eventCalls === 1) {
        return eventBatch([
          clientFrontendEvent("progress_event", {
            progress_event: progressEvent({
              workflow_run_id: "wr_retained",
              status: "step_started",
              user_visible_summary: "Retained progress is running."
            })
          })
        ], "1");
      }
      return eventBatch([], String(eventCalls));
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");
  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);

  await app.refreshRuntimeStatus();

  assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);
  assert.equal(dom.window.document.querySelector("#pipeline-progress-title")?.textContent, "Kernel step running");
});

test("terminal kernel progress remains visible across one polling interval", async () => {
  const originalNow = Date.now;
  let nowMs = 1_000;
  let eventCalls = 0;
  Date.now = () => nowMs;
  try {
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
        eventCalls += 1;
        if (eventCalls === 1) {
          return eventBatch([
            clientFrontendEvent("progress_event", {
              progress_event: progressEvent({
                workflow_run_id: "wr_terminal_hold",
                status: "failed",
                user_visible_summary: "Terminal progress is retained."
              })
            })
          ], "1");
        }
        return eventBatch([], String(eventCalls));
      }
    });

    await app.boot();
    await app.switchAgent("pipeline");
    nowMs += 2_500;
    await app.refreshRuntimeStatus();

    assert.equal(dom.window.document.querySelector("#pipeline-progress-panel")?.hidden, false);
    assert.equal(dom.window.document.querySelector("#pipeline-progress-title")?.textContent, "Kernel workflow failed");
  } finally {
    Date.now = originalNow;
  }
});
