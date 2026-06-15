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

test("pipeline adapter calls permanent workflow tools directly with empty arguments", async () => {
  const calls = [];
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => {
      calls.push([name, args]);
      return kernelToolResponse(name);
    },
    listKernelTools: async () => [],
    listEventScopedTools: async () => ({})
  });
  adapter.permanentTools = PERMANENT_AGENT_TOOL_NAMES.map((name) => ({ name, description: name, inputSchema: { type: "object", properties: {}, additionalProperties: false } }));
  adapter.permanentToolMap = new Map(adapter.permanentTools.map((tool) => [tool.name, tool]));

  const result = await adapter.callVisibleTool("empty_database_default_taxonomy_default_projections", {}, {
    conversationRef: "session-1",
    turnRef: "chat-turn",
    clientRequestId: "req-1"
  });

  assert.equal(result.tool_name, "empty_database_default_taxonomy_default_projections");
  assert.deepEqual(calls[0], [
    "empty_database_default_taxonomy_default_projections",
    {}
  ]);
});

test("pipeline adapter exposes transient active workflow summary after workflow starter call", async () => {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name) => kernelToolResponse(name, {
      status: "accepted",
      effect: "started",
      user_visible_summary: "Workflow accepted."
    }),
    listKernelTools: async () => [],
    listEventScopedTools: async () => ({})
  });
  adapter.permanentTools = PERMANENT_AGENT_TOOL_NAMES.map((name) => ({ name, description: name, inputSchema: { type: "object", properties: {}, additionalProperties: false } }));
  adapter.permanentToolMap = new Map(adapter.permanentTools.map((tool) => [tool.name, tool]));

  await adapter.callVisibleTool("empty_database_no_semantic_release", {});

  const status = adapter.cachedStatus();
  assert.equal(status.active_workflow_run?.workflow_tool, "empty_database_no_semantic_release");
  assert.equal(status.active_workflow_run?.status, "step_started");
});

test("pipeline adapter forwards only opaque resume option refs for the generic continue tool", async () => {
  const calls = [];
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => {
      calls.push([name, args]);
      return kernelToolResponse(name, {
        effect: "workflow_completed",
        continued_workflow_tool: "empty_database_default_taxonomy_default_projections"
      });
    },
    listKernelTools: async () => [],
    listEventScopedTools: async () => ({})
  });
  adapter.permanentTools = PERMANENT_MCP_TOOLS;
  adapter.permanentToolMap = new Map(adapter.permanentTools.map((tool) => [tool.name, tool]));

  const result = await adapter.callVisibleTool("kernel_continue_resumable_workflow", {
    resume_option_ref: "opaque:resume-default"
  });

  assert.equal(result.tool_name, "kernel_continue_resumable_workflow");
  assert.deepEqual(calls[0], [
    "kernel_continue_resumable_workflow",
    { resume_option_ref: "opaque:resume-default" }
  ]);
});

test("pipeline adapter rejects model-authored arguments before any MCP call", async () => {
  const calls = [];
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args) => {
      calls.push([name, args]);
      return kernelToolResponse(name);
    },
    listKernelTools: async () => [],
    listEventScopedTools: async () => ({})
  });
  adapter.permanentTools = PERMANENT_AGENT_TOOL_NAMES.map((name) => ({ name, description: name, inputSchema: { type: "object", properties: {}, additionalProperties: false } }));
  adapter.permanentToolMap = new Map(adapter.permanentTools.map((tool) => [tool.name, tool]));

  const result = await adapter.callVisibleTool("manual_pipeline_run", { path_value: "C:\\Secret" });

  assert.equal(result.status, "rejected");
  assert.equal(result.reason, "agent_authored_arguments_rejected");
  assert.equal(calls.length, 0);
});
