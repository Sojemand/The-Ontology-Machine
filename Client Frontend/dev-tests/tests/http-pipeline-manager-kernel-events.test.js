import assert from "node:assert/strict";
import test from "node:test";

import { mergeKernelMirrorEventsIntoHistory } from "../../client_frontend/pipeline_agent/context_policy.js";
import { createApplication } from "../../server/index.js";
import {
  clientFrontendEvent,
  eventBatch,
  hostBridgeResponse,
  interactionRequest,
  interactionResponse,
  mirrorEvent
} from "./pipeline-agent-test-fixtures.js";
import { createHttpServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

test("kernel event polling appends mirror events to internal pipeline history", async () => {
  const fixture = createHttpServerFixture("vp-http-kernel-", { pipeline_root: "C:\\Pipeline" });
  const histories = [];
  const agent = {
    async initialize() {
      return true;
    },
    async chat() {
      throw new Error("chat must not be used");
    },
    async listKernelEvents(_cursor, { history = [] }) {
      histories.push(history);
      const currentMirror = mirrorEvent({ mirror_event_id: `mev_${histories.length}` });
      return {
        batch: eventBatch([clientFrontendEvent("mirror_event", { mirror_event: currentMirror })], String(histories.length)),
        history: mergeKernelMirrorEventsIntoHistory(history, [currentMirror]),
        autoResults: []
      };
    },
    async submitInteractionResponse() {
      throw new Error("not used");
    },
    async cancelInteraction() {
      throw new Error("not used");
    },
    async cancelActiveRun() {
      return { status: "ok" };
    },
    async status() {
      return { available: true, reason: "", permission_status: null, permission_warning: "" };
    },
    close() {}
  };
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => agent
  });
  const baseUrl = await listen(app.server);
  try {
    const first = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/events`);
    const cookie = first.headers.get("set-cookie");
    assert.equal(first.status, 200);
    const second = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/events?after=1`, {
      headers: { cookie }
    });
    assert.equal(second.status, 200);
    assert.equal(histories.length, 2);
    assert.equal(histories[0].length, 0);
    assert.equal(histories[1].filter((entry) => entry.role === "kernel").length, 1);
    assert.equal((await second.json()).schema_version, "kernel.client_frontend_event_batch.v1");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("interaction response and cancel routes relay payloads to the kernel bridge without using chat", async () => {
  const fixture = createHttpServerFixture("vp-http-kernel-", { pipeline_root: "C:\\Pipeline" });
  const request = interactionRequest();
  const submitPayloads = [];
  const cancelPayloads = [];
  let chatCalled = false;
  const submitAutoResults = [{
    answer: "Kernel completion explain.",
    sources: [],
    mode: "analytic",
    exactness: "evidence_grounded",
    metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
    ambiguities: [],
    method: "kernel_auto_report"
  }];
  const cancelAutoResults = [{
    answer: "Kernel cancellation explain.",
    sources: [],
    mode: "analytic",
    exactness: "evidence_grounded",
    metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
    ambiguities: [],
    method: "kernel_auto_report"
  }];
  const agent = {
    async initialize() {
      return true;
    },
    async chat() {
      chatCalled = true;
      throw new Error("chat must not be used");
    },
    async listKernelEvents() {
      return { batch: eventBatch([]), history: [], autoResults: [] };
    },
    async submitInteractionResponse(_interactionRequestId, payload) {
      submitPayloads.push(payload);
      return {
        bridge_response: hostBridgeResponse({
          persisted_response: payload
        }),
        event_batch: eventBatch([]),
        autoResults: submitAutoResults
      };
    },
    async cancelInteraction(_interactionRequestId, payload) {
      cancelPayloads.push(payload);
      return {
        bridge_response: hostBridgeResponse({
          status: "cancelled",
          persisted_response: payload
        }),
        event_batch: eventBatch([]),
        autoResults: cancelAutoResults
      };
    },
    async cancelActiveRun() {
      return { status: "ok" };
    },
    async status() {
      return { available: true, reason: "", permission_status: null, permission_warning: "" };
    },
    close() {}
  };
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => agent
  });
  const baseUrl = await listen(app.server);
  try {
    const submitted = interactionResponse(request, { path_value: "C:\\Workspace\\Chosen" });
    const submitRes = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/interactions/${request.interaction_request_id}/response`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(submitted)
    });
    assert.equal(submitRes.status, 200);
    assert.equal(submitPayloads.length, 1);
    assert.equal(submitPayloads[0].path_value, "C:\\Workspace\\Chosen");
    const submitBody = await submitRes.json();
    assert.equal(submitBody.auto_results.length, 1);
    assert.equal(submitBody.auto_results[0].answer, "Kernel completion explain.");

    const cancelled = interactionResponse(request, {
      response_status: "cancelled",
      cancellation_reason: "user_cancelled",
      path_value: undefined
    });
    const cancelRes = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/interactions/${request.interaction_request_id}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cancelled)
    });
    assert.equal(cancelRes.status, 200);
    assert.equal(cancelPayloads.length, 1);
    assert.equal(cancelPayloads[0].cancellation_reason, "user_cancelled");
    const cancelBody = await cancelRes.json();
    assert.equal(cancelBody.auto_results.length, 1);
    assert.equal(cancelBody.auto_results[0].answer, "Kernel cancellation explain.");

    const expired = interactionResponse(request, {
      response_status: "expired",
      cancellation_reason: "timeout",
      path_value: undefined
    });
    const expiredRes = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/interactions/${request.interaction_request_id}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(expired)
    });
    assert.equal(expiredRes.status, 200);
    assert.equal(submitPayloads.length, 1);
    assert.equal(cancelPayloads.length, 2);
    assert.equal(cancelPayloads[1].response_status, "expired");
    const expiredBody = await expiredRes.json();
    assert.equal(expiredBody.auto_results.length, 1);
    assert.equal(expiredBody.auto_results[0].answer, "Kernel cancellation explain.");
    assert.equal(chatCalled, false);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
