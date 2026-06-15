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

test("empty database completion explain_now events expose structured next-step context to the agent", async () => {
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
              frontend_event_id: "cfe_empty_db_completion",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_empty_db_completion",
              created_at: "2026-05-10T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_empty_db_completion",
                is_kernel_auto_call: true,
                event_type: "workflow_completed",
                user_visible_summary: "Artifact Tree and empty Corpus DB were created. No Semantic Release is attached yet. Created paths: Artifact Tree path: C:\\Target\\Artifact Tree; Corpus DB path: C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite. Choose next whether to attach the default Semantic Release or create a custom taxonomy and then custom projections.",
                current_state_summary: "no_semantic_release",
                workflow_run_id: "wr_empty_db_completion",
                workflow_tool: "empty_database_no_semantic_release",
                agent_explanation_guidance: {
                  response_mode: "explain_now",
                  technical_detail_focus_path: "technical_detail_ref.workflow_completion"
                },
                technical_detail_ref: {
                  kind: "database_creation_workflow_completion",
                  workflow_completion: {
                    final_state: "no_semantic_release",
                    outcome: {
                      artifact_tree_created: true,
                      empty_database_created: true,
                      semantic_release_attached: false,
                      semantic_release_active: false,
                      database_ready_for_ingest: false
                    },
                    created_artifacts: {
                      artifact_root_path: "C:\\Target\\Artifact Tree",
                      database_path: "C:\\Target\\Artifact Tree\\Corpus\\kernel_test.sqlite"
                    },
                    next_step_options: [
                      {
                        option_id: "attach_default_semantic_release",
                        surface_availability: {
                          mode: "explicit_kernel_resume_selection",
                          direct_agent_tool_available: false,
                          first_agent_tool: "kernel_resume_state",
                          continuation_workflow_tool: "empty_database_default_taxonomy_default_projections",
                          requires_explicit_resume_selection: true,
                          resume_step_id: "dc_export_default_release"
                        }
                      },
                      {
                        option_id: "create_custom_taxonomy_then_projection",
                        surface_availability: {
                          mode: "explicit_kernel_resume_selection",
                          first_agent_tool: "kernel_resume_state",
                          continuation_workflow_tool: "create_custom_taxonomy_path",
                          required_followup_agent_tool: "create_custom_projection_path",
                          direct_agent_tool_available: false,
                          requires_explicit_resume_selection: true
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
      return { choices: [{ message: { content: "The empty database was created and the next decision is whether to continue with the default Semantic Release path or the custom taxonomy and projection path." } }] };
    }
  });

  try {
    const result = await agent.listKernelEvents("", { conversationRef: "pipeline-session", history: [] });
    const kernelContextMessage = providerMessages.find((message) => String(message?.content || "").includes("Kernel mirror event."));

    assert.equal(result.autoResults.length, 1);
    assert.match(result.autoResults[0].answer, /empty database was created/i);
    assert.equal(result.autoResults[0].history.some((entry) => entry.role === "user"), false);
    assert.equal(completionCalls, 1);
    assert.ok(kernelContextMessage);
    assert.match(String(kernelContextMessage.content), /attach_default_semantic_release/);
    assert.match(String(kernelContextMessage.content), /create_custom_taxonomy_path/);
    assert.match(String(kernelContextMessage.content), /create_custom_projection_path/);
    assert.match(String(kernelContextMessage.content), /C:\\\\Target\\\\Artifact Tree/);
    assert.match(String(kernelContextMessage.content), /kernel_test\.sqlite/);
    assert.match(String(kernelContextMessage.content), /database_ready_for_ingest/);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
