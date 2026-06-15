import assert from "node:assert/strict";

import { createAppHarness, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch } from "./pipeline-agent-test-fixtures.js";

const VALUE_FIELDS = [
  "path_value",
  "text_value",
  "choice_id",
  "selected_database_paths",
  "confirmation_decision",
  "recovery_id",
  "cancellation_reason"
];

export async function assertSingleDialogResponseValue(testCase) {
  const captured = [];
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
        clientFrontendEvent("interaction_request", {
          interaction_request: testCase.request
        })
      ], "1"),
    submitKernelInteractionResponse: async (_interactionRequestId, payload) => {
      captured.push(payload);
      return {
        bridge_response: {
          schema_version: "semantic_control_kernel.host_bridge_response.v1",
          status: "accepted",
          user_visible_summary: "Interaction accepted."
        },
        event_batch: eventBatch([])
      };
    },
    cancelKernelInteraction: async (_interactionRequestId, payload) => {
      captured.push(payload);
      return {
        bridge_response: {
          schema_version: "semantic_control_kernel.host_bridge_response.v1",
          status: "closed",
          user_visible_summary: "Interaction closed."
        },
        event_batch: eventBatch([])
      };
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, false, testCase.dialogType);
  testCase.interact(dom.window.document);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(captured.length, 1, testCase.dialogType);
  const presentFields = VALUE_FIELDS.filter((field) => captured[0][field] !== undefined);
  assert.equal(presentFields.length, 1, testCase.dialogType);
  assert.equal(presentFields[0], testCase.expectedField, testCase.dialogType);
}
