import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, progressEvent } from "./pipeline-agent-test-fixtures.js";

const CASES = [
  ["step_started", "Kernel step running", "running"],
  ["step_completed", "Kernel step completed", "done"],
  ["waiting_for_user", "Waiting for your input", "waiting"],
  ["blocked", "Kernel blocked", "warning"],
  ["retrying", "Kernel retrying", "running"],
  ["cancelled", "Kernel cancelled", "warning"],
  ["completed", "Kernel workflow completed", "done"],
  ["failed", "Kernel workflow failed", "error"]
];

for (const [status, title, state] of CASES) {
  test(`kernel progress maps status ${status}`, async () => {
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
              status,
              user_visible_summary: `Status ${status}.`,
              ordinal: 2,
              total_steps: 5
            })
          })
        ], "1")
    });

    await app.boot();
    await app.switchAgent("pipeline");

    const panel = dom.window.document.querySelector("#pipeline-progress-panel");
    assert.equal(panel?.hidden, false);
    assert.equal(panel?.dataset.state, state);
    assert.equal(dom.window.document.querySelector("#pipeline-progress-title")?.textContent, title);
    assert.equal(dom.window.document.querySelector("#pipeline-progress-count")?.textContent, "2/5");
    assert.match(dom.window.document.querySelector("#pipeline-progress-summary")?.textContent || "", new RegExp(status));
  });
}

const CREATION_WORKFLOW_TOOLS = [
  "empty_database_no_semantic_release",
  "empty_database_default_taxonomy_no_projections",
  "empty_database_default_taxonomy_default_projections"
];

for (const workflowTool of CREATION_WORKFLOW_TOOLS) {
  test(`active workflow run fallback shows progress panel for ${workflowTool}`, async () => {
    const { app, dom } = createAppHarness({
      getHealth: async () =>
        health({
          pipeline_manager: {
            available: true,
            reason: "",
            tool_count: 30,
            semantic_control_kernel_tool_count: 30,
            permission_status: null,
            permission_warning: "",
            active_workflow_run: {
              workflow_run_id: `wr_${workflowTool}`,
              workflow_tool: workflowTool,
              status: "step_started",
              step_id: "client_frontend_handoff",
              step_label: "Workflow handoff",
              user_visible_summary: "Workflow wurde an den Kernel uebergeben."
            }
          }
        }),
      getPipelineKernelEvents: async () => eventBatch([], "1")
    });

    await app.boot();
    await app.switchAgent("pipeline");

    const panel = dom.window.document.querySelector("#pipeline-progress-panel");
    assert.equal(panel?.hidden, false);
    assert.equal(panel?.dataset.state, "running");
    assert.match(dom.window.document.querySelector("#pipeline-progress-title")?.textContent || "", /Kernel workflow/i);
    assert.match(dom.window.document.querySelector("#pipeline-progress-summary")?.textContent || "", /Kernel/);
  });
}
