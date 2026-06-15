import assert from "node:assert/strict";
import test from "node:test";

import {
  createPipelineKernelAdapter,
  PERMANENT_AGENT_TOOL_NAMES,
  validateSemanticControlKernelToolSurface
} from "../../client_frontend/pipeline_agent/kernel_client.js";
import {
  LEGACY_MCP_TOOLS,
  NON_KERNEL_MCP_TOOLS,
  PERMANENT_MCP_TOOLS
} from "./pipeline-agent-test-fixtures.js";

test("pipeline manager exposes exactly the permanent Semantic Control Kernel tools", () => {
  const definitions = validateSemanticControlKernelToolSurface([...NON_KERNEL_MCP_TOOLS, ...PERMANENT_MCP_TOOLS]);

  assert.deepEqual(definitions.map((tool) => tool.name), PERMANENT_AGENT_TOOL_NAMES);
  for (const tool of definitions) {
    if (tool.name === "kernel_continue_resumable_workflow") {
      assert.deepEqual(Object.keys(tool.inputSchema.properties), ["resume_option_ref"]);
      assert.deepEqual(tool.inputSchema.required, ["resume_option_ref"]);
      continue;
    }
    assert.deepEqual(tool.inputSchema, {
      type: "object",
      properties: {},
      additionalProperties: false
    });
  }
});

test("non-kernel MCP primitives are filtered out of the model-visible tool surface", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async () => {
      throw new Error("not used");
    },
    listKernelTools: async () => [...PERMANENT_MCP_TOOLS, ...NON_KERNEL_MCP_TOOLS],
    listEventScopedTools: async () => ({})
  });

  await adapter.bootstrap();

  assert.equal(adapter.toolDefinitions().some((tool) => tool.name === "healthcheck_mcp"), false);
  assert.equal(adapter.toolDefinitions().length, PERMANENT_AGENT_TOOL_NAMES.length);
});

test("legacy Agent-facing tool names make initialization fail unavailable", () => {
  assert.throws(
    () => validateSemanticControlKernelToolSurface([...PERMANENT_MCP_TOOLS, ...LEGACY_MCP_TOOLS.slice(0, 1)]),
    /retired Agent tools/i
  );
});

test("old generic virtual tools are not exported", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async () => {
      throw new Error("not used");
    },
    listKernelTools: async () => PERMANENT_MCP_TOOLS,
    listEventScopedTools: async () => ({})
  });

  await adapter.bootstrap();

  assert.equal(adapter.toolDefinitions().some((tool) => tool.name === "pipeline_action"), false);
  assert.equal(adapter.toolDefinitions().some((tool) => tool.name === "pipeline_continue"), false);
});
