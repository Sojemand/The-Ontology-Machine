import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES,
  validateSemanticControlKernelToolSurface
} from "../../client_frontend/pipeline_agent/kernel_client.js";
import { EMPTY_OBJECT_SCHEMA, PERMANENT_MCP_TOOLS } from "./pipeline-agent-test-fixtures.js";

const MODULE_ROOT = path.resolve(fileURLToPath(new URL("../../", import.meta.url)));
const AGENT_ROOT = path.join(MODULE_ROOT, "client_frontend", "pipeline_agent");
const EXPECTED_FORBIDDEN_NAMES = [
  "pipeline_action",
  "pipeline_continue",
  "llm_action_catalog",
  "open_workflow",
  "inspect_workflow",
  "execute_readonly_workflow_action",
  "execute_author_workflow_action",
  "execute_operator_workflow_action",
  "execute_admin_workflow_action",
  "interrupt_workflow",
  "close_workflow",
  "workflow_family_id",
  "workflow_revision",
  "action_token",
  "target_action_id",
  "x_action_catalog",
  "required_agent_level"
];

test("forbidden legacy names are isolated to the rejection constant and do not survive in active prompts or workflow code", () => {
  const files = [
    path.join(AGENT_ROOT, "prompt.js"),
    path.join(AGENT_ROOT, "workflow.js"),
    path.join(AGENT_ROOT, "chat_workflow.js"),
    path.join(AGENT_ROOT, "context_policy.js")
  ];
  const combined = files.map((filePath) => readFileSync(filePath, "utf8")).join("\n");

  for (const name of FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES) {
    assert.doesNotMatch(combined, new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("kernel client keeps the forbidden legacy surface inventory as runtime truth without leaking raw legacy strings into active source", () => {
  const kernelClientText = readFileSync(path.join(AGENT_ROOT, "kernel_client.js"), "utf8");

  assert.deepEqual(FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES, EXPECTED_FORBIDDEN_NAMES);
  for (const name of EXPECTED_FORBIDDEN_NAMES) {
    assert.doesNotMatch(kernelClientText, new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.throws(
      () => validateSemanticControlKernelToolSurface([
        ...PERMANENT_MCP_TOOLS,
        {
          name,
          description: `Legacy tool ${name}.`,
          inputSchema: { ...EMPTY_OBJECT_SCHEMA }
        }
      ]),
      /retired Agent tools/i
    );
  }
  assert.match(kernelClientText, /FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES/);
  assert.doesNotMatch(kernelClientText, /callVirtualTool|pipeline_continue needs a pending action/i);
});
