import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createHttpServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

test("pipeline manager chat fails closed without a pipeline root", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/pipeline-manager/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Status?" })
    });
    assert.equal(res.status, 409);
    const body = await res.json();
    assert.equal(body.error, "Choose Pipeline Root Folder");
    assert.equal(body.field, "pipeline_root");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("pipeline manager chat uses an independent injected agent and history", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-", { pipeline_root: "C:\\Pipeline" });
  const captured = [];
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => ({
      async initialize() {
        return true;
      },
      async chat({ message, history }) {
        captured.push({ message, history });
        return {
          answer: `Pipeline: ${message}`,
          sources: [],
          mode: "analytic",
          exactness: "evidence_grounded",
          metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "pipeline_manager_agent",
          history: [...history, { role: "user", content: message }, { role: "assistant", content: `Pipeline: ${message}` }]
        };
      },
      async status() {
        return {
          available: true,
          reason: "",
          tool_count: 2,
          permission_status: { active_agent_level: "L2_OPERATOR", level_order: ["L0_READONLY", "L1_AUTHOR", "L2_OPERATOR", "L3_ADMIN"] },
          permission_warning: ""
        };
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);

  try {
    const first = await fetch(`${baseUrl}/api/v2/pipeline-manager/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Inspect" })
    });
    assert.equal(first.status, 200);
    const cookie = extractCookie(first);
    const second = await fetch(`${baseUrl}/api/v2/pipeline-manager/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(cookie ? { Cookie: cookie } : {}) },
      body: JSON.stringify({ message: "Weiter" })
    });
    assert.equal(second.status, 200);
    assert.equal((await second.json()).method, "pipeline_manager_agent");
    assert.equal(captured.length, 2);
    assert.equal(captured[0].history.length, 0);
    assert.equal(captured[1].history.length, 2);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("ontology agent chat uses an independent injected agent and history", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const captured = [];
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createOntologyAgentFn: () => ({
      async chat({ message, history }) {
        captured.push({ message, history });
        return {
          answer: `Ontology: ${message}`,
          sources: [],
          mode: "analytic",
          exactness: "evidence_grounded",
          metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "ontology_agent",
          history: [...history, { role: "user", content: message }, { role: "assistant", content: `Ontology: ${message}` }]
        };
      },
      countDocuments() {
        return 1;
      },
      resolveImage() {
        return { available: false, path: null };
      },
      resolveSource() {
        return null;
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);

  try {
    const first = await fetch(`${baseUrl}/api/v2/ontology-agent/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Create lens" })
    });
    assert.equal(first.status, 200);
    const cookie = extractCookie(first);
    const second = await fetch(`${baseUrl}/api/v2/ontology-agent/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(cookie ? { Cookie: cookie } : {}) },
      body: JSON.stringify({ message: "Continue" })
    });
    assert.equal(second.status, 200);
    assert.equal((await second.json()).method, "ontology_agent");
    assert.equal(captured.length, 2);
    assert.equal(captured[0].history.length, 0);
    assert.equal(captured[1].history.length, 2);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
