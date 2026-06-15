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

test("submitted interaction responses reload a fresh Kernel event snapshot so follow-up dialogs are not skipped", async () => {
  const firstRequest = interactionRequest({
    interaction_request_id: "irq_create_parent",
    interaction_function: "choose_artifact_root_folder",
    user_visible_title: "Choose Artifact Root Folder",
    user_visible_summary: "Choose the parent folder for the new Artifact Tree.",
    created_at: "2026-05-10T10:00:00Z",
    mirror_event_id: "mev_create_parent"
  });
  const secondRequest = interactionRequest({
    interaction_request_id: "irq_name_root",
    interaction_function: "name_artifact_root_folder",
    interaction_kind: "input",
    dialog_type: "folder_create_picker",
    user_visible_title: "Name Artifact Root Folder",
    user_visible_summary: "Enter the full folder path for the new Artifact Tree.",
    response_shape: "path_value_or_text_value",
    created_at: "2026-05-10T10:00:05Z",
    mirror_event_id: "mev_name_root"
  });
  const requestedCursors = [];
  const adapter = createPipelineKernelAdapter({
    callKernelTool: async (name, args = {}) => {
      if (name === "kernel_list_client_frontend_events") {
        const cursor = String(args.cursor || "");
        requestedCursors.push(cursor);
        if (requestedCursors.length === 1) {
          return eventBatch([
            clientFrontendEvent("interaction_request", {
              interaction_request: firstRequest
            }, {
              frontend_event_id: "cfe_first_dialog",
              mirror_event_id: "mev_create_parent",
              created_at: firstRequest.created_at
            })
          ], "3");
        }
        if (cursor === "") {
          return eventBatch([
            clientFrontendEvent("interaction_request", {
              interaction_request: secondRequest
            }, {
              frontend_event_id: "cfe_second_dialog",
              mirror_event_id: "mev_name_root",
              created_at: secondRequest.created_at
            })
          ], "4");
        }
        return eventBatch([], "3");
      }
      if (name === "kernel_submit_user_interaction_response") {
        return hostBridgeResponse({
          persisted_response: args.response
        });
      }
      return await defaultKernelCallTool(name, args);
    },
    listKernelTools: async () => [...PERMANENT_MCP_TOOLS],
    listEventScopedTools: async () => ({
      schema_version: "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
      mirror_event_id: "",
      recovery_event_id: "",
      state_snapshot_id: "",
      status: "active",
      tool_definitions: []
    })
  });

  await adapter.bootstrap();
  await adapter.listKernelEvents("");
  const result = await adapter.submitInteractionResponse(
    firstRequest.interaction_request_id,
    interactionResponse(firstRequest, { path_value: "C:\\Workspace\\Artifacts" })
  );

  assert.deepEqual(requestedCursors, ["", ""]);
  assert.equal(result.event_batch.events.length, 1);
  assert.equal(
    result.event_batch.events[0]?.interaction_request?.interaction_request_id,
    secondRequest.interaction_request_id
  );
});

test("submitted interaction responses surface explain_now completion auto-results immediately", async () => {
  const root = createPipelineRoot();
  let completionCalls = 0;
  const request = interactionRequest({
    interaction_request_id: "irq_name_database",
    interaction_function: "name_database",
    interaction_kind: "input",
    dialog_type: "text_input",
    response_shape: "text_value"
  });
  const agent = createPipelineManagerAgent({
    pipelineRoot: root,
    getRuntimeConfig: () => ({ context_limit: 60_000 }),
    getFrontendPolicy: () => null,
    mcpClientFactory: () => createFakeClient({
      callTool: async (name, args) => {
        if (name === "kernel_submit_user_interaction_response") {
          return hostBridgeResponse({
            persisted_response: args.response
          });
        }
        if (name === "kernel_list_client_frontend_events") {
          return eventBatch([
            clientFrontendEvent("mirror_event", {
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_empty_db_completion_submit",
                is_kernel_auto_call: true,
                event_type: "workflow_completed",
                workflow_run_id: "wr_empty_db_completion_submit",
                workflow_tool: "empty_database_no_semantic_release",
                user_visible_summary: "Artifact Tree and empty Corpus DB were created. No Semantic Release is attached yet.",
                current_state_summary: "no_semantic_release",
                agent_explanation_guidance: {
                  response_mode: "explain_now"
                }
              })
            }, {
              frontend_event_id: "cfe_empty_db_completion_submit",
              mirror_event_id: "mev_empty_db_completion_submit",
              created_at: "2026-05-10T00:00:00Z"
            })
          ], "1");
        }
        return await defaultKernelCallTool(name, args);
      }
    }),
    createChatCompletionFn: async () => {
      completionCalls += 1;
      return {
        choices: [{
          message: {
            content: "The empty database was created and still needs a Semantic Release before ingest can run."
          }
        }]
      };
    }
  });

  try {
    const result = await agent.submitInteractionResponse(
      request.interaction_request_id,
      interactionResponse(request, {
        path_value: undefined,
        text_value: "Artifact Tree Kernel Test"
      }),
      {
        conversationRef: "pipeline-session",
        history: []
      }
    );

    assert.equal(result.autoResults.length, 1);
    assert.match(result.autoResults[0].answer, /empty database was created/i);
    assert.equal(completionCalls, 1);
    assert.equal(
      result.history.some((entry) => entry.role === "assistant" && /semantic release/i.test(String(entry.content || ""))),
      true
    );
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
