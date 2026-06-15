import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";
import {
  clientFrontendEvent,
  eventBatch,
  interactionRequest,
  mirrorEvent
} from "./pipeline-agent-test-fixtures.js";

test("recovery dialogs and support bundle notices render without exposing event-scoped tools as workflow buttons", async () => {
  const request = interactionRequest({
    dialog_type: "support_bundle_notice",
    user_visible_title: "Support bundle available",
    user_visible_summary: "A support bundle is ready for inspection."
  });
  const recoveryMirror = mirrorEvent({
    mirror_event_id: "mev_recovery",
    recovery_event_id: "rev_recovery",
    event_type: "recovery_state",
    severity: "recoverable_error",
    user_visible_summary: "Recovery options are available.",
    allowed_agent_tools: ["kernel_open_support_bundle", "kernel_open_recovery_dialog"],
    recovery_options: [{ recovery_id: "rec_bundle", label: "Open support bundle" }]
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
          permission_warning: "",
          pending_kernel_event_count: 2
        }
      }),
    getPipelineKernelEvents: async () =>
      eventBatch([
        clientFrontendEvent("mirror_event", {
          mirror_event: recoveryMirror
        }),
        clientFrontendEvent("interaction_request", {
          interaction_request: request
        })
      ], "1")
  });

  await app.boot();
  await app.switchAgent("pipeline");

  assert.match(dom.window.document.querySelector("#pipeline-permission-status")?.textContent || "", /Recovery options are available/);
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, false);
  assert.match(dom.window.document.querySelector("#kernel-dialog-summary")?.textContent || "", /support bundle/i);
  assert.doesNotMatch(dom.window.document.querySelector("#messages")?.textContent || "", /kernel_open_support_bundle|kernel_open_recovery_dialog/);
});
