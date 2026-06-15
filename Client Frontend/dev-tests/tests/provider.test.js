import assert from "node:assert/strict";
import test from "node:test";

import {
  defaultBaseUrl,
  fetchModelCatalog,
  runEmbeddingHealthCheck,
  runLlmHealthCheck
} from "../../server/provider.js";

function mockFetch(handler) {
  const original = globalThis.fetch;
  globalThis.fetch = handler;
  return () => { globalThis.fetch = original; };
}

function jsonResponse(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

// ---------------------------------------------------------------------------
// defaultBaseUrl
// ---------------------------------------------------------------------------

test("defaultBaseUrl keeps empty provider on OpenAI but unknown providers on custom compat", () => {
  assert.equal(defaultBaseUrl("openai"), "https://api.openai.com/v1");
  assert.equal(defaultBaseUrl("unknown"), "http://127.0.0.1:1234/v1");
  assert.equal(defaultBaseUrl(""), "https://api.openai.com/v1");
});

test("defaultBaseUrl returns Mammouth URL for mammouth provider", () => {
  assert.equal(defaultBaseUrl("mammouth"), "https://api.mammouth.ai/v1");
});

// ---------------------------------------------------------------------------
// fetchModelCatalog
// ---------------------------------------------------------------------------

test("fetchModelCatalog returns fallback when no API key for OpenAI", async () => {
  const restore = mockFetch(() => { throw new Error("should not be called"); });
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "", apiKey: "" });
    assert.equal(result.source, "fallback");
    assert.ok(result.llm_models.length > 0);
    assert.ok(result.embedding_models.length > 0);
    assert.ok(result.error);
  } finally {
    restore();
  }
});

test("fetchModelCatalog returns fallback on network error", async () => {
  const restore = mockFetch(() => { throw new Error("network down"); });
  try {
    const result = await fetchModelCatalog({ provider: "mammouth", baseUrl: "https://broken.example.com/v1", apiKey: "key" });
    assert.equal(result.source, "fallback");
    assert.match(result.error, /network down/);
  } finally {
    restore();
  }
});

test("fetchModelCatalog extracts IDs from data array format", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    data: [
      { id: "gpt-4.1", object: "model" },
      { id: "gpt-4o", object: "model" },
      { id: "text-embedding-3-small", object: "model" }
    ]
  }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.equal(result.source, "live");
    assert.ok(result.llm_models.includes("gpt-4.1"));
    assert.ok(result.llm_models.includes("gpt-4o"));
    assert.ok(result.embedding_models.includes("text-embedding-3-small"));
  } finally {
    restore();
  }
});

test("fetchModelCatalog extracts IDs from models array format", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    models: [
      { id: "model-alpha" },
      { id: "model-embedding-beta" }
    ]
  }));
  try {
    const result = await fetchModelCatalog({ provider: "mammouth", baseUrl: "https://api.mammouth.ai/v1", apiKey: "" });
    assert.equal(result.source, "live");
    assert.ok(result.llm_models.includes("model-alpha"));
    assert.ok(result.embedding_models.includes("model-embedding-beta"));
  } finally {
    restore();
  }
});

test("fetchModelCatalog separates embedding vs LLM models by regex", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    data: [
      { id: "gpt-4o" },
      { id: "text-embedding-3-large" },
      { id: "text-embedding-ada-002" },
      { id: "gpt-4.1-mini" }
    ]
  }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.ok(!result.llm_models.includes("text-embedding-3-large"), "embedding model should not be in llm_models");
    assert.ok(!result.llm_models.includes("text-embedding-ada-002"), "ada model should not be in llm_models");
    assert.ok(result.embedding_models.includes("text-embedding-3-large"));
    assert.ok(result.embedding_models.includes("text-embedding-ada-002"));
    assert.ok(result.llm_models.includes("gpt-4o"));
    assert.ok(result.llm_models.includes("gpt-4.1-mini"));
  } finally {
    restore();
  }
});

// ---------------------------------------------------------------------------
// runLlmHealthCheck
// ---------------------------------------------------------------------------

test("runLlmHealthCheck returns status ok with timing on success", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    choices: [{ message: { role: "assistant", content: "Hi" } }]
  }));
  try {
    const result = await runLlmHealthCheck({
      baseUrl: "https://api.openai.com/v1",
      apiKey: "sk-test",
      model: "gpt-4.1"
    });
    assert.equal(result.status, "ok");
    assert.match(result.message, /Connection OK/);
    assert.match(result.message, /\d+ms/);
  } finally {
    restore();
  }
});

test("runLlmHealthCheck throws on non-200 response", async () => {
  const restore = mockFetch(() => jsonResponse(401, {
    error: { message: "Invalid API key" }
  }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "bad-key", model: "gpt-4.1" }),
      /Invalid API key/
    );
  } finally {
    restore();
  }
});

// ---------------------------------------------------------------------------
// runEmbeddingHealthCheck
// ---------------------------------------------------------------------------

test("runEmbeddingHealthCheck returns dimensions on success", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    data: [{ embedding: Array.from({ length: 1536 }, () => 0.01) }]
  }));
  try {
    const result = await runEmbeddingHealthCheck({
      baseUrl: "https://api.openai.com/v1",
      apiKey: "sk-test",
      model: "text-embedding-3-small"
    });
    assert.equal(result.status, "ok");
    assert.match(result.message, /1536 dimensions/);
  } finally {
    restore();
  }
});

test("runEmbeddingHealthCheck throws when no dimensions returned", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [{ embedding: [] }] }));
  try {
    await assert.rejects(
      () => runEmbeddingHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "bad-model" }),
      /No embedding dimensions/
    );
  } finally {
    restore();
  }
});

