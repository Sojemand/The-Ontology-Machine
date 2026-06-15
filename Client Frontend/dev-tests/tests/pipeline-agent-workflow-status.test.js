import assert from "node:assert/strict";
import { mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { buildPipelineSystemPrompt } from "../../client_frontend/pipeline_agent/prompt.js";
import { createPipelineKernelAdapter } from "../../client_frontend/pipeline_agent/kernel_client.js";
import { createPipelineManagerAgent } from "../../client_frontend/pipeline_agent/workflow.js";
import {
  createFakeClient,
  createPipelineRoot,
  defaultKernelCallTool,
  eventBatch,
  kernelToolResponse,
  mirrorEvent,
  NON_KERNEL_MCP_TOOLS,
  PERMANENT_AGENT_TOOL_NAMES,
  PERMANENT_MCP_TOOLS,
  recoveryOption
} from "./pipeline-agent-test-fixtures.js";

test("pipeline manager status is driven by kernel_status instead of legacy inspection routes", async () => {
  const root = createPipelineRoot();
  const calls = [];
  let listToolCalls = 0;
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({}),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      listTools: async () => {
        listToolCalls += 1;
        return [...PERMANENT_MCP_TOOLS, ...NON_KERNEL_MCP_TOOLS];
      },
      callTool: async (name, args) => {
        calls.push([name, args]);
        return await defaultKernelCallTool(name, args);
      }
    })
  });

  try {
    const status = await agent.status();

    assert.equal(status.available, true);
    assert.equal(status.tool_count, PERMANENT_AGENT_TOOL_NAMES.length);
    assert.equal(status.semantic_control_kernel_tool_count, PERMANENT_AGENT_TOOL_NAMES.length);
    assert.equal(Boolean(status.kernel_status), true);
    assert.equal(status.raw_mcp_tool_count, PERMANENT_AGENT_TOOL_NAMES.length + NON_KERNEL_MCP_TOOLS.length);
    assert.equal(listToolCalls, 1);
    assert.equal(calls.some(([name]) => name === "kernel_status"), true);
    assert.deepEqual(calls.find(([name]) => name === "kernel_status")[1], {});
    assert.equal(calls.some(([name]) => name === "runtime_credentials_governance"), false);
    assert.equal(calls.some(([name]) => name === "inspect_workflow"), false);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("pipeline manager resolves relative pipeline root from the Client Frontend module folder", async () => {
  const root = createPipelineRoot();
  const moduleRoot = path.join(root, "Client Frontend");
  mkdirSync(moduleRoot, { recursive: true });
  const agent = createPipelineManagerAgent({
    pipelineRoot: "..",
    moduleRoot,
    getRuntimeConfig: () => ({}),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({})
  });

  try {
    const status = await agent.status();

    assert.equal(status.available, true);
    assert.equal(status.pipeline_root, root);
    assert.equal(status.mcp_server_dir, path.join(root, "07 - MCP Server"));
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("pipeline manager infers installed pipeline root from the Client Frontend module folder", async () => {
  const root = createPipelineRoot();
  mkdirSync(path.join(root, "08 - Semantic Control Kernel"), { recursive: true });
  const moduleRoot = path.join(root, "Client Frontend");
  mkdirSync(moduleRoot, { recursive: true });
  const agent = createPipelineManagerAgent({
    pipelineRoot: "",
    moduleRoot,
    getRuntimeConfig: () => ({}),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({})
  });

  try {
    const status = await agent.status();

    assert.equal(status.available, true);
    assert.equal(status.pipeline_root, root);
    assert.equal(status.mcp_server_dir, path.join(root, "07 - MCP Server"));
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("pipeline manager abort delegates to kernel_cancel_active_run and never to interrupt_workflow", async () => {
  const root = createPipelineRoot();
  const calls = [];
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({}),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        calls.push([name, args]);
        if (name === "kernel_cancel_active_run") {
          return kernelToolResponse(name, {
            effect: "none",
            cancel_status: "no_active_run",
            user_visible_summary: "No active Kernel workflow run is currently cancellable."
          });
        }
        return await defaultKernelCallTool(name, args);
      }
    })
  });

  try {
    const result = await agent.cancelActiveRun();

    assert.equal(result.tool_name, "kernel_cancel_active_run");
    assert.equal(result.cancel_status, "no_active_run");
    assert.equal(calls.some(([name]) => name === "kernel_cancel_active_run"), true);
    assert.equal(calls.some(([name]) => name === "interrupt_workflow"), false);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
