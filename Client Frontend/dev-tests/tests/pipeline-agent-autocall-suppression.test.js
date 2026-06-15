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

test("explain_now auto-call cannot restart a workflow from prior user context", async () => {
  const root = createPipelineRoot();
  const calls = [];
  let providerTools = null;
  let providerMessages = [];
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        calls.push([name, args]);
        if (name === "kernel_list_client_frontend_events") {
          return eventBatch([
            {
              schema_version: "kernel.client_frontend_event.v1",
              frontend_event_id: "cfe_ready_default_completion_context_guard",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_ready_default_completion_context_guard",
              created_at: "2026-05-10T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_ready_default_completion_context_guard",
                is_kernel_auto_call: true,
                event_type: "workflow_completed",
                user_visible_summary: "The ready default database was created.",
                current_state_summary: "semantic_release_active",
                workflow_run_id: "wr_ready_default_completion_context_guard",
                workflow_tool: "empty_database_default_taxonomy_default_projections",
                agent_explanation_guidance: {
                  response_mode: "explain_now",
                  technical_detail_focus_path: "technical_detail_ref.workflow_completion"
                },
                technical_detail_ref: {
                  kind: "database_creation_workflow_completion",
                  workflow_completion: {
                    final_state: "semantic_release_active",
                    outcome: {
                      artifact_tree_created: true,
                      empty_database_created: true,
                      semantic_release_active: true,
                      database_ready_for_ingest: true
                    },
                    created_artifacts: {
                      artifact_root_path: "C:\\Target\\Artifact Tree",
                      database_path: "C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite"
                    }
                  }
                }
              })
            }
          ]);
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async (_runtimeConfig, messages, tools) => {
      providerMessages = Array.isArray(messages) ? messages.map((message) => ({ ...message })) : [];
      providerTools = Array.isArray(tools) ? [...tools] : tools;
      return { choices: [{ message: { content: "Die fertige Standarddatenbank ist erstellt und ingest-bereit." } }] };
    }
  });

  try {
    const result = await agent.listKernelEvents("", {
      conversationRef: "pipeline-session",
      history: [
        { role: "user", content: "Bau mir eine leere datenbank mit defaul release" },
        { role: "assistant", content: "Der Workflow wurde gestartet." }
      ]
    });

    assert.equal(result.autoResults.length, 1);
    assert.match(result.autoResults[0].answer, /ingest-bereit/i);
    assert.deepEqual(providerTools, []);
    assert.equal(providerMessages.some((message) => String(message?.content || "").includes("Bau mir eine leere datenbank")), false);
    assert.match(String(providerMessages[0]?.content || ""), /Explain only the latest Kernel mirror event/i);
    assert.equal(result.history.some((entry) => entry.role === "user" && /Bau mir eine leere datenbank/.test(entry.content)), true);
    assert.equal(calls.some(([name]) => name === "empty_database_default_taxonomy_default_projections"), false);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});

test("auto-call mirror events without explain_now do not trigger an agent response", async () => {
  const root = createPipelineRoot();
  let completionCalls = 0;
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        if (name === "kernel_list_client_frontend_events") {
          return eventBatch([
            {
              schema_version: "kernel.client_frontend_event.v1",
              frontend_event_id: "cfe_passive",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_passive",
              created_at: "2026-05-06T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_passive",
                recovery_event_id: "rev_passive",
                is_kernel_auto_call: true,
                state_snapshot_identity: { state_snapshot_id: "ss_passive" },
                event_type: "recovery_state",
                allowed_agent_tools: ["kernel_open_recovery_dialog"],
                recovery_options: [
                  recoveryOption({
                    recovery_id: "rcv_passive",
                    recovery_event_id: "rev_passive",
                    agent_tool: "kernel_open_recovery_dialog"
                  })
                ],
                agent_explanation_guidance: { response_mode: "wait_for_user" }
              })
            }
          ]);
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async () => {
      completionCalls += 1;
      return { choices: [{ message: { content: "This should not run." } }] };
    }
  });

  try {
    const result = await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });

    assert.equal(result.autoResults.length, 0);
    assert.equal(completionCalls, 0);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
