import assert from "node:assert/strict";
import { rmSync } from "node:fs";
import test from "node:test";

import { createPipelineKernelAdapter } from "../../client_frontend/pipeline_agent/kernel_client.js";
import { createPipelineManagerAgent } from "../../client_frontend/pipeline_agent/workflow.js";
import {
  clientFrontendEvent,
  createFakeClient,
  createPipelineRoot,
  defaultKernelCallTool,
  eventBatch,
  hostBridgeResponse,
  interactionRequest,
  interactionResponse,
  kernelToolResponse,
  mirrorEvent,
  PERMANENT_MCP_TOOLS,
  progressEvent,
  recoveryOption
} from "./pipeline-agent-test-fixtures.js";

test("changing pipeline conversation scope clears cached dialog state from a previous session", async () => {
  const root = createPipelineRoot();
  let eventPollCount = 0;
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args = {}) => {
        if (name === "kernel_list_client_frontend_events") {
          eventPollCount += 1;
          return eventPollCount === 1
            ? eventBatch([
              clientFrontendEvent("progress_event", {
                progress_event: progressEvent({
                  workflow_run_id: "wr_scope_one",
                  workflow_tool: "empty_database_no_semantic_release",
                  status: "waiting_for_user",
                  step_id: "dc_collect_target",
                  step_label: "dc_collect_target",
                  user_visible_summary: "Choose the parent folder for the new Artifact Tree."
                })
              }),
              clientFrontendEvent("interaction_request", {
                interaction_request: interactionRequest({
                  interaction_request_id: "irq_scope_one",
                  workflow_run_id: "wr_scope_one"
                })
              })
            ], "1")
            : eventBatch([], "0");
        }
        return await defaultKernelCallTool(name, args);
      }
    })
  });

  try {
    await agent.listKernelEvents("", { conversationRef: "pipeline-session-one", history: [] });
    let status = await agent.status({ fast: true });
    assert.equal(status.active_dialog?.interaction_request?.interaction_request_id, "irq_scope_one");

    await agent.listKernelEvents("", { conversationRef: "pipeline-session-two", history: [] });
    status = await agent.status({ fast: true });
    assert.equal(status.active_dialog, null);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("real user workflow requests ignore stale dialog mirror history after status reconciliation", async () => {
  const root = createPipelineRoot();
  const calls = [];
  let completionCalls = 0;
  let firstProviderMessages = [];
  const staleDialogMirror = mirrorEvent({
    mirror_event_id: "mev_stale_default_dialog",
    event_type: "selection_dialog_opened",
    workflow_run_id: "wr_stale_default_dialog",
    workflow_tool: "empty_database_default_taxonomy_default_projections",
    user_visible_summary: "Choose the parent folder for the new Artifact Tree.",
    progress_event: progressEvent({
      workflow_run_id: "wr_stale_default_dialog",
      workflow_tool: "empty_database_default_taxonomy_default_projections",
      status: "waiting_for_user",
      step_id: "dc_collect_target",
      step_label: "dc_collect_target",
      user_visible_summary: "Choose the parent folder for the new Artifact Tree."
    })
  });
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        calls.push([name, args]);
        if (name === "empty_database_default_taxonomy_default_projections") {
          return kernelToolResponse(name, {
            status: "accepted",
            effect: "started",
            workflow_run_id: "wr_fresh_default_dialog",
            user_visible_summary: "The Kernel started the default database creation workflow.",
            mirror_event: mirrorEvent({
              mirror_event_id: "mev_fresh_default_started",
              event_type: "progress",
              workflow_run_id: "wr_fresh_default_dialog",
              workflow_tool: "empty_database_default_taxonomy_default_projections",
              user_visible_summary: "The Kernel started the default database creation workflow."
            })
          });
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      completionCalls += 1;
      if (completionCalls === 1) {
        firstProviderMessages = Array.isArray(messages) ? messages.map((message) => ({ ...message })) : [];
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "tc_default_database",
                function: {
                  name: "empty_database_default_taxonomy_default_projections",
                  arguments: "{}"
                }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Der Kernel hat den neuen Default-Release-Datenbankworkflow gestartet." } }] };
    }
  });

  try {
    const result = await agent.chat({
      message: "bau mir mal eine leere datenbank mit default release",
      history: [{
        role: "kernel",
        content: JSON.stringify(staleDialogMirror),
        kernel_mirror_event: staleDialogMirror
      }],
      ownerId: "pipeline-session"
    });

    const firstSystemMessage = String(firstProviderMessages[0]?.content || "");
    const providerContext = firstProviderMessages.map((message) => String(message?.content || "")).join("\n");

    assert.match(result.answer, /gestartet/i);
    assert.equal(calls.some(([name]) => name === "kernel_status"), true);
    assert.equal(calls.some(([name]) => name === "empty_database_default_taxonomy_default_projections"), true);
    assert.match(firstSystemMessage, /Current Kernel activity snapshot from this turn/i);
    assert.match(firstSystemMessage, /active_workflow_run=none/);
    assert.doesNotMatch(providerContext, /mev_stale_default_dialog/);
    assert.doesNotMatch(providerContext, /Choose the parent folder for the new Artifact Tree/);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
