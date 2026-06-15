import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, deferred, health } from "./main-app-fixtures.js";
import { eventBatch } from "./pipeline-agent-test-fixtures.js";

test("pipeline chat handoff shows local progress before sendChat returns", async () => {
  const chat = deferred();
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
    getPipelineKernelEvents: async () => eventBatch([], "1"),
    sendChat: async () => {
      await chat.promise;
      return {
        answer: "Der Workflow wurde gestartet.",
        sources: []
      };
    }
  });

  await app.boot();
  await app.switchAgent("pipeline");

  const input = dom.window.document.querySelector("#chat-input");
  const form = dom.window.document.querySelector("#chat-form");
  input.value = "erstelle eine leere datenbank ohne semantic release";
  form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));

  const panel = dom.window.document.querySelector("#pipeline-progress-panel");
  assert.equal(panel?.hidden, false);
  assert.match(dom.window.document.querySelector("#pipeline-progress-title")?.textContent || "", /Taxonomy Agent is processing the request/i);
  assert.match(dom.window.document.querySelector("#pipeline-progress-summary")?.textContent || "", /Request sent/i);

  chat.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
});
