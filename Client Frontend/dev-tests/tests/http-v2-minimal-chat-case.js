import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createHttpServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

test("v2 chat route uses the injected minimal agent", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const captured = [];
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => ({
      async chat({ message, history }) {
        captured.push({ message, history });
        return {
          answer: "Es gibt 1 Stromdokument.",
          sources: [{
            id: "doc-1",
            title: "Stromrechnung Januar",
            type: "invoice",
            date: "2024-01-10",
            actor: "Alpha GmbH",
            page: 1,
            page_count: 1,
            source_refs: ["page1_para_1"],
            snippet: "Strom Abschlag Januar",
            image_url: "/api/image/doc-1/1",
            viewer_available: false
          }],
          mode: "lookup",
          exactness: "evidence_grounded",
          metrics: { scope_documents: 1, matched_documents: 1, matched_occurrences: 1, aggregated_values: null },
          ambiguities: [],
          method: "minimal_agent",
          history: [...history, { role: "user", content: message }, { role: "assistant", content: "Es gibt 1 Stromdokument." }]
        };
      },
      countDocuments() {
        return 1;
      },
      resolveImage() {
        return { available: false, path: null };
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Wie oft kommt Strom vor?" })
    });
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.method, "minimal_agent");
    assert.equal(body.metrics.matched_documents, 1);
    assert.equal(captured.length, 1);
    assert.equal(captured[0].history.length, 0);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
