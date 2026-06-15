import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, progressEvent } from "./pipeline-agent-test-fixtures.js";

test("pipeline abort button routes through the kernel cancellation endpoint", async () => {
  let cancelledRunId = "";
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
          pending_kernel_event_count: 1,
          active_pipeline_run: {
            status: "running",
            run_id: "run-abort"
          }
        }
      }),
    getPipelineKernelEvents: async () =>
      eventBatch([
        clientFrontendEvent("progress_event", {
          progress_event: progressEvent({
            workflow_run_id: "run-abort",
            status: "step_started",
            user_visible_summary: "Kernel run is active."
          })
        })
      ], "1"),
    cancelPipelineRun: async (runId) => {
      cancelledRunId = runId || "";
      return { status: "cancelled", run_cancelled: true, run_id: runId, message: "Kernel cancellation requested." };
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");
  const button = dom.window.document.querySelector("#pipeline-abort-button");
  assert.equal(button?.hidden, false);
  button?.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(cancelledRunId, "run-abort");
  assert.match(dom.window.document.querySelector("#chat-status")?.textContent || "", /Kernel cancellation requested/);
});
