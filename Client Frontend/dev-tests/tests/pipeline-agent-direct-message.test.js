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

test("emit_direct_message mirror events post the Kernel report without a model round-trip", async () => {
  const root = createPipelineRoot();
  let completionCalls = 0;
  const reportText = "# Sample Analysis Report\n\nThe sample set is ready for review.";
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
              frontend_event_id: "cfe_report",
              frontend_event_kind: "mirror_event",
              mirror_event_id: "mev_report",
              created_at: "2026-05-10T00:00:00Z",
              mirror_event: mirrorEvent({
                mirror_event_id: "mev_report",
                is_kernel_auto_call: true,
                event_type: "progress",
                user_visible_summary: reportText,
                agent_explanation_guidance: {
                  response_mode: "emit_direct_message",
                  suppress_kernel_history: true
                }
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

    assert.equal(result.autoResults.length, 1);
    assert.equal(result.autoResults[0].answer, reportText);
    assert.equal(result.autoResults[0].history.some((entry) => entry.role === "kernel"), false);
    assert.equal(completionCalls, 0);
  } finally {
    agent.close();
    rmSync(root, { recursive: true, force: true });
  }
});
