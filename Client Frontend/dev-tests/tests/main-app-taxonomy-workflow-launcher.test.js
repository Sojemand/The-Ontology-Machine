import assert from "node:assert/strict";
import test from "node:test";

import { PERMANENT_AGENT_TOOL_NAMES } from "../../client_frontend/pipeline_agent/kernel_tool_surface.js";
import {
  TAXONOMY_WORKFLOW_OPTIONS,
  buildTaxonomyWorkflowCommand
} from "../../client_frontend/browser/main_app/taxonomy_workflow_launcher.ts";
import { createAppHarness, health } from "./main-app-fixtures.js";

test("taxonomy workflow launcher mirrors non-kernel permanent workflow tools", () => {
  const expectedWorkflowNames = PERMANENT_AGENT_TOOL_NAMES.filter((name) => !name.startsWith("kernel_"));
  assert.deepEqual(TAXONOMY_WORKFLOW_OPTIONS.map((option) => option.toolName), expectedWorkflowNames);
  assert.ok(TAXONOMY_WORKFLOW_OPTIONS.every((option) => buildTaxonomyWorkflowCommand(option.toolName).includes(option.toolName)));
});

test("taxonomy workflow launcher is visible only for the Taxonomy Agent and starts the selected workflow", async () => {
  const sent = [];
  const { app, dom } = createAppHarness({
    getHealth: async () =>
      health({
        pipeline_manager: {
          available: true,
          reason: "",
          tool_count: 16,
          semantic_control_kernel_tool_count: 16,
          permission_status: null,
          permission_warning: "",
          pending_kernel_event_count: 0
        }
      }),
    sendChat: async (message, agent) => {
      sent.push({ message, agent });
      return { answer: "Workflow accepted.", sources: [] };
    }
  });

  await app.boot();

  const launcher = dom.window.document.querySelector("#taxonomy-workflow-launcher");
  const menuButton = dom.window.document.querySelector("#taxonomy-workflow-menu-button");
  const menuList = dom.window.document.querySelector("#taxonomy-workflow-menu-list");

  assert.equal(launcher?.hidden, true);

  await app.switchAgent("pipeline");

  assert.equal(launcher?.hidden, false);
  assert.equal(menuList?.hidden, true);
  assert.ok(dom.window.document.querySelector('[data-tool-name="manual_pipeline_run"]'));

  menuButton?.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  assert.equal(menuList?.hidden, false);

  dom.window.document.querySelector('[data-tool-name="manual_pipeline_run"]')?.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.deepEqual(sent, [
    {
      agent: "pipeline",
      message: "Run Taxonomy Agent workflow `manual_pipeline_run`. This was selected from the workflow menu; use the matching visible Kernel workflow tool."
    }
  ]);
  assert.equal(menuList?.hidden, true);
  assert.match(dom.window.document.querySelector("#messages")?.textContent || "", /Workflow accepted/);
});
