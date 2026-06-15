import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, progressEvent } from "./pipeline-agent-test-fixtures.js";

test("pipeline progress panel renders Kernel progress events for the pipeline agent tab", async () => {
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
          pending_kernel_event_count: 1
        }
      }),
    getPipelineKernelEvents: async () =>
      eventBatch([
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            status: "step_started",
            step_label: "Analyze input",
            ordinal: 1,
            total_steps: 3,
            user_visible_summary: "The Kernel is analyzing the input set."
          })
        })
      ], "1")
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const document = dom.window.document;
  assert.equal(document.querySelector("#pipeline-progress-panel")?.hidden, false);
  assert.equal(document.querySelector("#pipeline-progress-title")?.textContent, "Kernel step running");
  assert.equal(document.querySelector("#pipeline-progress-count")?.textContent, "1/3");
  assert.match(document.querySelector("#pipeline-progress-summary")?.textContent || "", /analyzing the input set/i);
  assert.match(document.querySelector("#pipeline-stage-list")?.textContent || "", /Analyze input/);
});

test("pipeline progress panel renders orchestrator module rows from snapshot refs", async () => {
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
          pending_kernel_event_count: 1
        }
      }),
    getPipelineKernelEvents: async () =>
      eventBatch([
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            status: "step_started",
            step_label: "Orchestrator",
            user_visible_summary: "Ingestion: 0/1 complete; current large.pdf",
            artifact_refs: [{
              kind: "orchestrator_stage_statuses",
              stages: [
                { name: "Intake", status: "Fertig", detail: "1 input file" },
                { name: "Interpreter", status: "Verarbeite...", detail: "large.pdf", progress_current: 12, progress_total: 59, progress_label: "Requests" },
                { name: "Validator", status: "Bereit", detail: "" },
                { name: "Error Cases", status: "Found", detail: "2 source file(s) in folder | failed_page_13.json" }
              ]
            }]
          })
        })
      ], "1")
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const text = dom.window.document.querySelector("#pipeline-stage-list")?.textContent || "";
  assert.match(text, /Intake/);
  assert.match(text, /Interpreter/);
  assert.match(text, /12\/59 Requests/);
  assert.match(text, /Validator/);
  assert.match(text, /Error Cases/);
  assert.match(text, /failed_page_13\.json/);
});
