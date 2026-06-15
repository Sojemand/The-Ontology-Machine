import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen, mergeCookies } from "./server-fixtures.js";

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test("concurrent chats for the same session stay serialized and ordered", async () => {
  const fixture = createSimpleServerFixture("vp-http-race-");
  const order = [];
  const histories = [];
  let releaseFirst;
  const firstGate = new Promise((resolve) => { releaseFirst = resolve; });
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => ({
      async chat({ message, history }) {
        histories.push({ message, history: [...history] });
        order.push(`start:${message}`);
        if (message === "first") await firstGate;
        order.push(`finish:${message}`);
        return {
          answer: `Antwort auf ${message}`,
          sources: [],
          mode: "lookup",
          exactness: "insufficient_evidence",
          metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "controlled",
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
    const bootstrap = await fetch(`${baseUrl}/api/chat/new`, { method: "POST" });
    const cookie = extractCookie(bootstrap);
    const firstRequest = fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ message: "first" })
    });
    await delay(30);

    const secondRequest = fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ message: "second" })
    });

    await delay(30);
    assert.deepEqual(order, ["start:first"]);

    releaseFirst();
    assert.equal((await firstRequest).status, 200);
    assert.equal((await secondRequest).status, 200);
    assert.deepEqual(order, ["start:first", "finish:first", "start:second", "finish:second"]);
    assert.equal(histories.length, 2);
    assert.equal(histories[0].history.length, 0);
    assert.equal(histories[1].history.length, 2);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("new chat waits for an active request and the next turn starts fresh", async () => {
  const fixture = createSimpleServerFixture("vp-http-race-");
  const histories = [];
  let releaseActive;
  const activeGate = new Promise((resolve) => { releaseActive = resolve; });
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createMinimalAgentFn: () => ({
      async chat({ message, history }) {
        histories.push({ message, history: [...history] });
        if (message === "before reset") await activeGate;
        return {
          answer: `Antwort auf ${message}`,
          sources: [],
          mode: "lookup",
          exactness: "insufficient_evidence",
          metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "controlled",
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
    const bootstrap = await fetch(`${baseUrl}/api/chat/new`, { method: "POST" });
    const cookie = extractCookie(bootstrap);
    const activeRequest = fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: cookie },
      body: JSON.stringify({ message: "before reset" })
    });
    await delay(30);

    let resetSettled = false;
    const resetRequest = fetch(`${baseUrl}/api/chat/new`, {
      method: "POST",
      headers: { Cookie: cookie }
    }).then((response) => {
      resetSettled = true;
      return response;
    });

    await delay(30);
    assert.equal(resetSettled, false);

    releaseActive();
    assert.equal((await activeRequest).status, 200);
    const resetResponse = await resetRequest;
    assert.equal(resetResponse.status, 200);

    const refreshedCookie = mergeCookies(cookie, extractCookie(resetResponse));
    const nextChat = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: refreshedCookie },
      body: JSON.stringify({ message: "after reset" })
    });
    assert.equal(nextChat.status, 200);
    assert.equal(histories.length, 2);
    assert.equal(histories[0].history.length, 0);
    assert.equal(histories[1].history.length, 0);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
