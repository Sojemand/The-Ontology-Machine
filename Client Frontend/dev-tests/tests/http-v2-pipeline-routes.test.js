import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createHttpServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

test("pipeline manager cancel route delegates to the injected pipeline agent", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-", { pipeline_root: "C:\\Pipeline" });
  let seenRunId = "";
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => ({
      async initialize() {
        return true;
      },
      async chat() {
        throw new Error("not used");
      },
      async cancelActiveRun(runId) {
        seenRunId = runId;
        return { status: "cancelled", run_cancelled: true, run_id: runId };
      },
      async status() {
        return { available: true, reason: "", permission_status: null, permission_warning: "" };
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);
  try {
    const res = await fetch(`${baseUrl}/api/v2/pipeline-manager/run/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: "run-123" })
    });
    assert.equal(res.status, 200);
    assert.equal(seenRunId, "run-123");
    assert.equal((await res.json()).status, "cancelled");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("pipeline manager kernel reset route requires confirmation and delegates to the agent", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-", { pipeline_root: "C:\\Pipeline" });
  let resetReason = "";
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => ({
      async initialize() {
        return true;
      },
      async chat() {
        throw new Error("not used");
      },
      async resetKernelRuntimeState({ reason }) {
        resetReason = reason;
        return {
          status: "ok",
          reset_id: "rst-test",
          created_at: "2026-05-09T10:00:00Z",
          archived_path_count: 3,
          preserved_paths: ["receipts"],
          reason,
          message: "Kernel reset complete."
        };
      },
      async status() {
        return { available: true, reason: "", permission_status: null, permission_warning: "" };
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);
  try {
    const rejected = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "wrong" })
    });
    assert.equal(rejected.status, 400);

    const accepted = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "RESET_KERNEL_RUNTIME_STATE", reason: "manual test reset" })
    });
    assert.equal(accepted.status, 200);
    assert.equal(resetReason, "manual test reset");
    assert.equal((await accepted.json()).archived_path_count, 3);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("pipeline manager kernel interaction normalizes declined confirmations to rejected", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-", { pipeline_root: "C:\\Pipeline" });
  let seenPayload = null;
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => ({
      async initialize() {
        return true;
      },
      async chat() {
        throw new Error("not used");
      },
      async submitInteractionResponse(_interactionRequestId, payload) {
        seenPayload = payload;
        return {
          bridge_response: { status: "accepted", user_visible_summary: "ok" },
          event_batch: { events: [] },
          autoResults: []
        };
      },
      async cancelInteraction() {
        throw new Error("not used");
      },
      async status() {
        return { available: true, reason: "", permission_status: null, permission_warning: "" };
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);
  try {
    const res = await fetch(`${baseUrl}/api/v2/pipeline-manager/kernel/interactions/irq-test/response`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schema_version: "kernel.user_interaction_response.v1",
        interaction_request_id: "irq-test",
        response_status: "submitted",
        target_identity: {},
        state_snapshot_identity: {},
        host_surface_identity: "client_frontend",
        interaction_response_id: "uir-test",
        submitted_at: "2026-05-31T08:30:00Z",
        confirmation_decision: "declined"
      })
    });
    assert.equal(res.status, 200);
    assert.equal(seenPayload?.confirmation_decision, "rejected");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("v2 document route is gone", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);
  try {
    const res = await fetch(`${baseUrl}/api/v2/documents/doc-1`);
    assert.equal(res.status, 404);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
