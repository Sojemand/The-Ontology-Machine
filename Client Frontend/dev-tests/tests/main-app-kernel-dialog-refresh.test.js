import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, deferred, health } from "./main-app-fixtures.js";
import { clientFrontendEvent, eventBatch, interactionRequest, progressEvent } from "./pipeline-agent-test-fixtures.js";

test("pipeline chat refreshes kernel events immediately so creation target dialog opens after workflow start", async () => {
  const request = interactionRequest({
    dialog_type: "folder_picker",
    interaction_function: "choose_artifact_root_folder",
    user_visible_title: "Choose Artifact Root Folder",
    user_visible_summary: "Choose the parent folder for the new Artifact Tree."
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
    sendChat: async () => ({
      answer: "Der Workflow wurde gestartet.\n\nNächster Schritt: Bitte wähle den übergeordneten Ordner für den neuen Artifact Tree.",
      sources: []
    }),
    getPipelineKernelEvents: async () => {
      kernelEventPollCount += 1;
      if (kernelEventPollCount < 3) {
        return eventBatch([], String(kernelEventPollCount));
      }
      return eventBatch([
        clientFrontendEvent("interaction_request", {
          interaction_request: request
        })
      ], String(kernelEventPollCount));
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");
  const input = dom.window.document.querySelector("#chat-input");
  const form = dom.window.document.querySelector("#chat-form");
  input.value = "ich will eine leere datenbank ohne semantic release bauen";
  form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, false);
  assert.match(dom.window.document.querySelector("#kernel-dialog-title")?.textContent || "", /choose artifact root folder/i);
  assert.match(dom.window.document.querySelector("#kernel-dialog-summary")?.textContent || "", /artifact tree/i);
  assert.ok(kernelEventPollCount >= 3);
});

test("active kernel dialog preserves a typed path draft across runtime refreshes", async () => {
  const request = interactionRequest({
    dialog_type: "folder_picker",
    interaction_function: "choose_artifact_root_folder",
    user_visible_title: "Choose Artifact Root Folder",
    user_visible_summary: "Choose the parent folder for the new Artifact Tree."
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
          clientFrontendEvent("interaction_request", {
            interaction_request: request
          })
        ], String(kernelEventPollCount))
        : eventBatch([], String(kernelEventPollCount));
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const input = dom.window.document.querySelector("#path-value");
  input.value = "C:\\Workspace\\Artifact Root";
  input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  const originalInputNode = input;

  await app.refreshRuntimeStatus();
  await app.refreshRuntimeStatus();

  const refreshedInput = dom.window.document.querySelector("#path-value");
  assert.equal(refreshedInput, originalInputNode);
  assert.equal(refreshedInput?.value, "C:\\Workspace\\Artifact Root");
  assert.equal(dom.window.document.querySelector("#kernel-dialog-panel")?.hidden, false);
});

test("name_database renders a single-line database-name field with .db guidance", async () => {
  const request = interactionRequest({
    interaction_function: "name_database",
    interaction_kind: "input",
    dialog_type: "text_input",
    response_shape: "text_value",
    user_visible_title: "Name Database",
    user_visible_summary: "Enter the database name for the new Corpus database.",
    prefilled_values: { text_value: "Artifact Tree" }
  });
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
          interaction_request: request
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
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const input = dom.window.document.querySelector("#text-value");
  assert.equal(input?.tagName, "INPUT");
  assert.equal(dom.window.document.querySelector("textarea#text-value"), null);
  assert.match(dom.window.document.querySelector(".kernel-dialog-field span")?.textContent || "", /database name/i);
  assert.match(dom.window.document.querySelector(".kernel-dialog-hint")?.textContent || "", /\.db/i);

  input.value = "corpus";
  dom.window.document.querySelector("#kernel-dialog-actions button")?.click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(captured.length, 1);
  assert.equal(captured[0].text_value, "corpus");
});
