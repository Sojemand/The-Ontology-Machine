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

test("ready default database completion explain_now events expose runnable next-step context to the agent", async () => {
  const root = createPipelineRoot();
  let completionCalls = 0;
  let providerMessages = [];
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
              frontend_event_id: "cfe_ready_default_completion",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_ready_default_completion",
              created_at: "2026-05-10T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_ready_default_completion",
                is_kernel_auto_call: true,
                event_type: "workflow_completed",
                user_visible_summary: "Artifact Tree, empty Corpus DB and the complete default Semantic Release were created. Created paths: Artifact Tree path: C:\\Target\\Artifact Tree; Corpus DB path: C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite; Default Semantic Release path: C:\\Target\\Artifact Tree\\Semantic Release\\default. The Semantic Release is active, so the database is ready for ingest.",
                current_state_summary: "semantic_release_active",
                workflow_run_id: "wr_ready_default_completion",
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
                      semantic_release_attached: true,
                      semantic_release_active: true,
                      database_ready_for_ingest: true
                    },
                    created_artifacts: {
                      artifact_root_path: "C:\\Target\\Artifact Tree",
                      database_path: "C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite",
                      default_release_path: "C:\\Target\\Artifact Tree\\Semantic Release\\default"
                    },
                    next_step_options: [
                      { option_id: "manual_pipeline_run", surface_availability: { first_agent_tool: "manual_pipeline_run" } },
                      { option_id: "database_modify_taxonomy", surface_availability: { first_agent_tool: "database_modify_taxonomy" } },
                      { option_id: "database_modify_projections", surface_availability: { first_agent_tool: "database_modify_projections" } },
                      { option_id: "kernel_status", surface_availability: { first_agent_tool: "kernel_status" } }
                    ]
                  }
                }
              })
            }
          ]);
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      completionCalls += 1;
      providerMessages = Array.isArray(messages) ? messages.map((message) => ({ ...message })) : [];
      return { choices: [{ message: { content: "The default Semantic Release is active, so the empty database is ready for ingest." } }] };
    }
  });

  try {
    const result = await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });
    const kernelContextMessage = providerMessages.find((message) => String(message?.content || "").includes("Kernel mirror event."));

    assert.equal(result.autoResults.length, 1);
    assert.match(result.autoResults[0].answer, /ready for ingest/i);
    assert.equal(result.autoResults[0].history.some((entry) => entry.role === "user"), false);
    assert.equal(completionCalls, 1);
    assert.ok(kernelContextMessage);
    assert.match(String(kernelContextMessage.content), /manual_pipeline_run/);
    assert.match(String(kernelContextMessage.content), /database_modify_taxonomy/);
    assert.match(String(kernelContextMessage.content), /database_modify_projections/);
    assert.match(String(kernelContextMessage.content), /C:\\\\Target\\\\Artifact Tree/);
    assert.match(String(kernelContextMessage.content), /kernel_test\.sqlite/);
    assert.match(String(kernelContextMessage.content), /semantic_release_active/);
    assert.match(String(kernelContextMessage.content), /database_ready_for_ingest/);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
