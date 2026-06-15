import assert from "node:assert/strict";
import test from "node:test";

import { createApiClient, extractErrorMessage, requestWithFetch } from "../../src/api/client.ts";

test("extractErrorMessage prefers structured JSON errors and falls back to raw text", () => {
  const response = new Response("", { status: 503, statusText: "Service Unavailable" });

  assert.equal(extractErrorMessage(response, JSON.stringify({ error: "kaputt" })), "kaputt");
  assert.equal(extractErrorMessage(response, JSON.stringify({ message: "auch kaputt" })), "auch kaputt");
  assert.equal(extractErrorMessage(response, "plain text failure"), "plain text failure");
  assert.equal(extractErrorMessage(response, "   "), "HTTP 503");
});

test("requestWithFetch returns undefined for 204 responses", async () => {
  const fetchImpl = async () => new Response(null, { status: 204 });

  const result = await requestWithFetch(fetchImpl, "/api/test");
  assert.equal(result, undefined);
});

test("requestWithFetch keeps same-origin credentials and default JSON headers", async () => {
  let seenInit;
  const fetchImpl = async (_input, init) => {
    seenInit = init;
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  };

  const result = await requestWithFetch(fetchImpl, "/api/test", {
    method: "POST",
    body: JSON.stringify({ hello: "world" })
  });

  assert.deepEqual(result, { ok: true });
  assert.equal(seenInit.credentials, "same-origin");
  assert.equal(new Headers(seenInit.headers).get("Content-Type"), "application/json");
});

test("requestWithFetch preserves explicit content type and surfaces text errors", async () => {
  let seenInit;
  const fetchImpl = async (_input, init) => {
    seenInit = init;
    return new Response("validation failed", { status: 422 });
  };

  await assert.rejects(
    () =>
      requestWithFetch(fetchImpl, "/api/upload", {
        method: "POST",
        headers: { "Content-Type": "multipart/form-data" }
      }),
    /validation failed/
  );

  assert.equal(new Headers(seenInit.headers).get("Content-Type"), "multipart/form-data");
});

test("createApiClient serializes chat payloads with the shared request helper", async () => {
  let seenInput = "";
  let seenInit;
  const client = createApiClient(async (input, init) => {
    seenInput = String(input);
    seenInit = init;
    return new Response(JSON.stringify({ answer: "ok", sources: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  });

  const result = await client.sendChat("Hallo Welt");

  assert.equal(seenInput, "/api/v2/chat");
  assert.equal(seenInit.method, "POST");
  assert.equal(seenInit.body, JSON.stringify({ message: "Hallo Welt" }));
  assert.equal(result.answer, "ok");
});

test("createApiClient routes pipeline manager calls to the pipeline surface", async () => {
  const seenInputs = [];
  const client = createApiClient(async (input) => {
    seenInputs.push(String(input));
    return new Response(JSON.stringify({ answer: "ok", sources: [], chats: [], messages: [], title: "ok", status: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  });

  await client.sendChat("Pipeline", "pipeline");
  await client.getChatHistory("pipeline");
  await client.newChat("pipeline");
  await client.restoreChat("abc", "pipeline");
  await client.cancelPipelineRun("run-1");

  assert.deepEqual(seenInputs, [
    "/api/v2/pipeline-manager/chat",
    "/api/pipeline-manager/history",
    "/api/pipeline-manager/new",
    "/api/pipeline-manager/restore/abc",
    "/api/v2/pipeline-manager/run/cancel"
  ]);
});

test("createApiClient routes ontology agent calls to the ontology surface", async () => {
  const seenInputs = [];
  const client = createApiClient(async (input) => {
    seenInputs.push(String(input));
    return new Response(JSON.stringify({ answer: "ok", sources: [], chats: [], messages: [], title: "ok", status: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  });

  await client.sendChat("Ontology", "ontology");
  await client.getChatHistory("ontology");
  await client.newChat("ontology");
  await client.restoreChat("abc", "ontology");

  assert.deepEqual(seenInputs, [
    "/api/v2/ontology-agent/chat",
    "/api/ontology-agent/history",
    "/api/ontology-agent/new",
    "/api/ontology-agent/restore/abc"
  ]);
});

