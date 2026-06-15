import assert from "node:assert/strict";
import test from "node:test";

import { runEmbeddingHealthCheck } from "../../server/provider.js";
import { jsonResponse, mockFetch } from "./provider-test-fixtures.js";

test("runEmbeddingHealthCheck throws when data array is empty", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [] }));
  try {
    await assert.rejects(
      () => runEmbeddingHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "text-embedding-3-small" }),
      /No embedding dimensions/
    );
  } finally {
    restore();
  }
});

test("runEmbeddingHealthCheck throws when embedding is null", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [{ embedding: null }] }));
  try {
    await assert.rejects(
      () => runEmbeddingHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "test" }),
      /No embedding dimensions/
    );
  } finally {
    restore();
  }
});

test("runEmbeddingHealthCheck reports correct dimension count", async () => {
  const restore = mockFetch(() => jsonResponse(200, { data: [{ embedding: Array.from({ length: 768 }, () => 0.01) }] }));
  try {
    const result = await runEmbeddingHealthCheck({
      baseUrl: "https://api.openai.com/v1",
      apiKey: "sk-test",
      model: "text-embedding-3-small"
    });
    assert.match(result.message, /768 dimensions/);
  } finally {
    restore();
  }
});
