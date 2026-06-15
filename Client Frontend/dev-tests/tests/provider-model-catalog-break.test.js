import assert from "node:assert/strict";
import test from "node:test";

import { fetchModelCatalog } from "../../server/provider.js";
import { jsonResponse, mockFetch } from "./provider-test-fixtures.js";

test("fetchModelCatalog with trailing slashes in base URL normalizes correctly", async () => {
  const restore = mockFetch((url) => {
    assert.ok(!url.includes("//models"), `URL should not have double slashes: ${url}`);
    return jsonResponse(200, { data: [{ id: "test-model" }] });
  });
  try {
    await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1///", apiKey: "sk-test" });
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles empty data array -- falls back to defaults", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [] }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.equal(result.source, "live");
    assert.ok(result.llm_models.length > 0);
    assert.ok(result.embedding_models.length > 0);
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles string-only model array", async () => {
  const restore = mockFetch(() => jsonResponse(200, ["model-a", "model-b", "text-embedding-foo"]));
  try {
    const result = await fetchModelCatalog({ provider: "mammouth", baseUrl: "https://api.mammouth.ai/v1", apiKey: "" });
    assert.equal(result.source, "live");
    assert.ok(result.llm_models.includes("model-a"));
    assert.ok(result.embedding_models.includes("text-embedding-foo"));
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles models with name field instead of id", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [{ name: "my-model" }, { name: "my-embedding" }] }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.ok(result.llm_models.includes("my-model"));
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles HTTP 500 error gracefully", async () => {
  const restore = mockFetch(() => jsonResponse(500, { error: { message: "Internal Server Error" } }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.equal(result.source, "fallback");
    assert.ok(result.error);
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles timeout gracefully", async () => {
  const restore = mockFetch(() => {
    throw new DOMException("The operation was aborted", "AbortError");
  });
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.equal(result.source, "fallback");
    assert.ok(result.error);
  } finally {
    restore();
  }
});

test("fetchModelCatalog with mammouth provider calls origin/public/models", async () => {
  let calledUrl = "";
  const restore = mockFetch((url) => {
    calledUrl = url;
    return jsonResponse(200, { models: [{ id: "mam-1" }] });
  });
  try {
    await fetchModelCatalog({ provider: "mammouth", baseUrl: "https://api.mammouth.ai/v1", apiKey: "" });
    assert.match(calledUrl, /mammouth\.ai\/public\/models/);
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles non-JSON response body", async () => {
  const restore = mockFetch(() => new Response("Not JSON", { status: 200, headers: { "Content-Type": "text/plain" } }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.equal(result.source, "fallback");
  } finally {
    restore();
  }
});

test("fetchModelCatalog handles empty response body", async () => {
  const restore = mockFetch(() => new Response("", { status: 200, headers: { "Content-Type": "application/json" } }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.ok(result.llm_models.length > 0);
  } finally {
    restore();
  }
});

test("fetchModelCatalog filters empty model IDs", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [{ id: "" }, { id: "valid-model" }, { id: null }, { name: "" }] }));
  try {
    const result = await fetchModelCatalog({ provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "sk-test" });
    assert.ok(!result.llm_models.includes(""));
    assert.ok(result.llm_models.includes("valid-model"));
  } finally {
    restore();
  }
});
