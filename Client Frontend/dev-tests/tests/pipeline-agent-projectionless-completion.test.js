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

test("default taxonomy no-projections completion explain_now events expose projection authoring context to the agent", async () => {
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
              frontend_event_id: "cfe_projectionless_completion",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_projectionless_completion",
              created_at: "2026-05-10T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_projectionless_completion",
                is_kernel_auto_call: true,
                event_type: "workflow_completed",
                user_visible_summary: "Artifact Tree, empty Corpus DB and the default taxonomy-only Semantic Release state were created. Created paths: Artifact Tree path: C:\\Target\\Artifact Tree; Corpus DB path: C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite; Default Semantic Release path: C:\\Target\\Artifact Tree\\Semantic Release\\releases\\default; Projectionless release state path: C:\\Target\\Artifact Tree\\Semantic Release\\staged\\taxonomy\\default_taxonomy_without_projections\\projectionless_release_state.json. Default projections are missing, so the database is not ready for ingest until custom projections are added.",
                current_state_summary: "semantic_release_incomplete",
                workflow_run_id: "wr_projectionless_completion",
                workflow_tool: "empty_database_default_taxonomy_no_projections",
                agent_explanation_guidance: {
                  response_mode: "explain_now",
                  technical_detail_focus_path: "technical_detail_ref.workflow_completion"
                },
                technical_detail_ref: {
                  kind: "database_creation_workflow_completion",
                  workflow_completion: {
                    final_state: "semantic_release_incomplete",
                    outcome: {
                      artifact_tree_created: true,
                      empty_database_created: true,
                      taxonomy_present: true,
                      projections_missing: true,
                      semantic_release_runnable: false,
                      database_ready_for_ingest: false
                    },
                    created_artifacts: {
                      artifact_root_path: "C:\\Target\\Artifact Tree",
                      database_path: "C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite",
                      default_release_path: "C:\\Target\\Artifact Tree\\Semantic Release\\releases\\default",
                      projectionless_release_state_path: "C:\\Target\\Artifact Tree\\Semantic Release\\staged\\taxonomy\\default_taxonomy_without_projections\\projectionless_release_state.json"
                    },
                    next_step_options: [
                      {
                        option_id: "create_custom_projection_path",
                        surface_availability: {
                          mode: "explicit_kernel_resume_selection",
                          direct_agent_tool_available: false,
                          first_agent_tool: "kernel_resume_state",
                          continuation_workflow_tool: "create_custom_projection_path",
                          requires_explicit_resume_selection: true,
                          resume_step_id: "proj_require_taxonomy"
                        }
                      }
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
      return { choices: [{ message: { content: "The database has the default taxonomy, but custom projections are still required before ingest." } }] };
    }
  });

  try {
    const result = await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });
    const kernelContextMessage = providerMessages.find((message) => String(message?.content || "").includes("Kernel mirror event."));

    assert.equal(result.autoResults.length, 1);
    assert.match(result.autoResults[0].answer, /custom projections are still required/i);
    assert.equal(result.autoResults[0].history.some((entry) => entry.role === "user"), false);
    assert.equal(completionCalls, 1);
    assert.ok(kernelContextMessage);
    assert.match(String(kernelContextMessage.content), /empty_database_default_taxonomy_no_projections/);
    assert.match(String(kernelContextMessage.content), /projectionless_release_state_path/);
    assert.match(String(kernelContextMessage.content), /create_custom_projection_path/);
    assert.match(String(kernelContextMessage.content), /kernel_resume_state/);
    assert.match(String(kernelContextMessage.content), /projections_missing/);
    assert.match(String(kernelContextMessage.content), /database_ready_for_ingest/);
    assert.match(String(kernelContextMessage.content), /semantic_release_incomplete/);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
