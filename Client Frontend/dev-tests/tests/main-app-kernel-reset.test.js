import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";

test("kernel reset button is gated to pipeline mode and confirms before reset", async () => {
  let resetCalls = 0;
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
    resetKernelRuntimeState: async () => {
      resetCalls += 1;
      return {
        status: "ok",
        reset_id: "rst-ui",
        created_at: "2026-05-09T10:00:00Z",
        archived_path_count: 4,
        preserved_paths: ["receipts"],
        reason: "client frontend kernel reset",
        message: "Kernel Runtime State wurde zurueckgesetzt."
      };
    }
  });
  dom.window.confirm = () => true;

  await app.boot();
  const button = dom.window.document.querySelector("#kernel-reset-button");
  assert.equal(button?.hidden, true);

  await app.switchAgent("pipeline");
  assert.equal(button?.hidden, false);
  assert.equal(button?.disabled, false);

  button?.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(resetCalls, 1);
  assert.match(dom.window.document.querySelector("#chat-status")?.textContent || "", /Kernel Runtime State/);
});
