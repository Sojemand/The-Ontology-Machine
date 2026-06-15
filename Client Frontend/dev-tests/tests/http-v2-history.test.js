import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createHttpServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

test("v2 chat restore rehydrates history for the next minimal-agent turn", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const seenHistories = [];
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => ({
      async chat({ message, history }) {
        seenHistories.push(history);
        return {
          answer: `Antwort auf ${message}`,
          sources: [],
          mode: "lookup",
          exactness: "insufficient_evidence",
          metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "minimal_agent",
          history: [...history, { role: "user", content: message }, { role: "assistant", content: `Antwort auf ${message}` }]
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
    const first = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Liste die Stromdokumente auf" })
    });
    assert.equal(first.status, 200);

    const cookie = extractCookie(first);
    const chatsRes = await fetch(`${baseUrl}/api/chat/history`, { headers: cookie ? { Cookie: cookie } : {} });
    const chatId = (await chatsRes.json()).chats?.[0]?.id;
    assert.ok(chatId);

    const restoreRes = await fetch(`${baseUrl}/api/chat/restore/${encodeURIComponent(chatId)}`, {
      method: "POST",
      headers: cookie ? { Cookie: cookie } : {}
    });
    assert.equal(restoreRes.status, 200);
    const restored = await restoreRes.json();
    assert.equal(restored.messages.at(-1).content, "Antwort auf Liste die Stromdokumente auf");

    const second = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(cookie ? { Cookie: cookie } : {}) },
      body: JSON.stringify({ message: "und welche davon sind Rechnungen?" })
    });
    assert.equal(second.status, 200);
    assert.equal(seenHistories.length, 2);
    assert.equal(seenHistories[1].length, 2);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("v2 chat restore refreshes stale source viewer metadata", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => ({
      async chat({ message, history }) {
        return {
          answer: `Antwort auf ${message}`,
          sources: [{
            id: "doc-1",
            title: "Alte Quelle",
            type: "invoice",
            date: "2024-01-10",
            actor: "Alpha GmbH",
            page: 1,
            page_count: 1,
            source_refs: ["page1_para_1"],
            snippet: "alt",
            image_url: "/api/image/doc-1/1",
            viewer_available: false,
            file_name: "alpha.pdf"
          }],
          mode: "lookup",
          exactness: "evidence_grounded",
          metrics: { scope_documents: 1, matched_documents: 1, matched_occurrences: 1, aggregated_values: null },
          ambiguities: [],
          method: "minimal_agent",
          history: [...history, { role: "user", content: message }, { role: "assistant", content: `Antwort auf ${message}` }]
        };
      },
      resolveSource(docId) {
        return {
          id: docId,
          title: "Aktuelle Quelle",
          type: "invoice",
          date: "2024-01-10",
          actor: "Alpha GmbH",
          page: 1,
          page_count: 3,
          source_refs: [],
          snippet: "aktuell",
          image_url: `/api/image/${encodeURIComponent(docId)}/1`,
          viewer_available: true,
          file_name: "alpha.pdf"
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
    const first = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Zeig mir die Quelle" })
    });
    assert.equal(first.status, 200);
    assert.equal((await first.json()).sources[0].viewer_available, false);

    const cookie = extractCookie(first);
    const chatsRes = await fetch(`${baseUrl}/api/chat/history`, { headers: cookie ? { Cookie: cookie } : {} });
    const chatId = (await chatsRes.json()).chats?.[0]?.id;
    assert.ok(chatId);

    const restoreRes = await fetch(`${baseUrl}/api/chat/restore/${encodeURIComponent(chatId)}`, {
      method: "POST",
      headers: cookie ? { Cookie: cookie } : {}
    });
    assert.equal(restoreRes.status, 200);
    const restoredSource = (await restoreRes.json()).messages.at(-1).sources[0];

    assert.equal(restoredSource.viewer_available, true);
    assert.equal(restoredSource.page_count, 3);
    assert.equal(restoredSource.title, "Aktuelle Quelle");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
