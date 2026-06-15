import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, deferred, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, interactionRequest, progressEvent } from "./pipeline-agent-test-fixtures.js";

test("stale kernel dialog responses keep the dialog visible with a stale status", async () => {
  const request = interactionRequest({ dialog_type: "folder_picker" });
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
          clientFrontendEvent("interaction_request", {
            interaction_request: request
          })
        ], "1")
        : eventBatch([], String(kernelEventPollCount));
    },
    submitKernelInteractionResponse: async () => ({
      bridge_response: {
        schema_version: "semantic_control_kernel.host_bridge_response.v1",
        status: "rejected_stale",
        user_visible_summary: "Response rejected.",
        error: {
          code: "stale",
          safe_message: "The dialog is stale."
        }
      },
      event_batch: eventBatch([])
    })
  });

  await app.boot();
  await app.switchAgent("pipeline");
  dom.window.document.querySelector("#path-value").value = "C:\\Workspace\\Changed";
  dom.window.document.querySelector("#kernel-dialog-actions button")?.click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  const panel = dom.window.document.querySelector("#kernel-dialog-panel");
  assert.equal(panel?.hidden, false);
  assert.equal(panel?.dataset.state, "stale");
  assert.match(dom.window.document.querySelector("#kernel-dialog-status")?.textContent || "", /stale/i);
  assert.equal(dom.window.document.querySelector("#path-value")?.disabled, false);
  assert.equal(dom.window.document.querySelector("#path-value")?.value, "C:\\Workspace\\Changed");
});

test("kernel dialog submit shows pending state immediately and prevents duplicate submits", async () => {
  const request = interactionRequest({ dialog_type: "folder_picker" });
  const submission = deferred();
  const captured = [];
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
          clientFrontendEvent("interaction_request", {
            interaction_request: request
          })
        ], "1")
        : eventBatch([], String(kernelEventPollCount));
    },
    submitKernelInteractionResponse: async (_interactionRequestId, payload) => {
      captured.push(payload);
      await submission.promise;
      return {
        bridge_response: {
          schema_version: "semantic_control_kernel.host_bridge_response.v1",
          status: "accepted",
          user_visible_summary: "Interaction accepted."
        },
        event_batch: eventBatch([])
      };
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");

  dom.window.document.querySelector("#path-value").value = "C:\\Workspace\\Chosen";
  dom.window.document.querySelector("#kernel-dialog-actions button")?.click();

  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.getAttribute("aria-busy"), "true");
  assert.equal(dom.window.document.querySelector("#path-value")?.disabled, true);
  assert.match(dom.window.document.querySelector("#kernel-dialog-status")?.textContent || "", /Kernel is processing/i);
  assert.match(dom.window.document.querySelector("#kernel-dialog-actions button")?.textContent || "", /Processing/i);
  assert.equal(Array.from(dom.window.document.querySelectorAll("#kernel-dialog-actions button")).every((button) => button.disabled), true);

  dom.window.document.querySelector("#kernel-dialog-actions button")?.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(captured.length, 1);

  submission.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, true);
});
