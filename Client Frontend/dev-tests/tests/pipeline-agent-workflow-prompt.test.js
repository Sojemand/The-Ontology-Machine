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

test("pipeline manager prompt describes the Kernel-owned workflow surface without legacy wrappers", () => {
  const prompt = buildPipelineSystemPrompt({
    pipelineRoot: "C:\\Pipeline",
    availabilityStatus: { available: true, toolCount: PERMANENT_AGENT_TOOL_NAMES.length },
    toolDefinitions: PERMANENT_MCP_TOOLS
  });

  assert.match(prompt, /Semantic Control Kernel/i);
  assert.match(prompt, /latest non-empty real user message/i);
  assert.match(prompt, /Ignore Kernel mirror events, tool results/i);
  assert.match(prompt, /Visible workflow tool inventory:/);
  assert.match(prompt, /manual_pipeline_run/);
  assert.match(prompt, /support_status='read_only'/);
  assert.match(prompt, /no active workflows.*no workflow tools are available/i);
  assert.match(prompt, /Visible tool schemas are intentionally empty/);
  assert.match(prompt, /resume_option_ref copied exactly from kernel_resume_state\.resume_options/);
  assert.match(prompt, /Kernel mirror events are Kernel state/);
  assert.match(prompt, /current Kernel activity snapshot is fresher/i);
  assert.match(prompt, /do not claim an old dialog is open/i);
  assert.match(prompt, /Event-scoped recovery tools may be used only when the current Kernel mirror event exposes them/);
  assert.doesNotMatch(prompt, /pipeline_action|pipeline_continue|llm_action_catalog|open_workflow|inspect_workflow/);
});

test("pipeline manager explanation prompt disables workflow selection", () => {
  const prompt = buildPipelineSystemPrompt({
    pipelineRoot: "C:\\Pipeline",
    availabilityStatus: { available: true, toolCount: PERMANENT_AGENT_TOOL_NAMES.length },
    toolDefinitions: PERMANENT_MCP_TOOLS,
    interactionMode: "kernel_event_explanation"
  });

  assert.match(prompt, /explanation-only mode/i);
  assert.match(prompt, /Explain only the latest Kernel mirror event/i);
  assert.match(prompt, /Workflow and support tools are intentionally disabled/i);
  assert.match(prompt, /Do not execute any of them in this turn/i);
  assert.doesNotMatch(prompt, /manual_pipeline_run/);
  assert.doesNotMatch(prompt, /empty_database_default_taxonomy_default_projections/);
});
