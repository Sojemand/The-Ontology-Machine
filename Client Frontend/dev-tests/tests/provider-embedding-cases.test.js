import assert from "node:assert/strict";
import test from "node:test";

import { embedTexts } from "../../server/provider.js";

import { jsonResponse, mockFetch } from "./provider-surface-support.js";

test("embedTexts returns embedding vectors from the public surface", async () => {
  const calls = [];
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    return jsonResponse(200, {
      data: [
        { embedding: [0.1, 0.2] },
        { embedding: [0.3, 0.4] }
      ]
    });
  });
  try {
    const result = await embedTexts({
      embedding_base_url: "https://api.openai.com/v1/",
      embedding_api_key: "sk-test",
      embedding_model: "text-embedding-3-small"
    }, ["eins", "zwei"]);
    const request = calls.at(0);
    const body = JSON.parse(request.init.body);

    assert.equal(request.url, "https://api.openai.com/v1/embeddings");
    assert.equal(body.model, "text-embedding-3-small");
    assert.deepEqual(body.input, ["eins", "zwei"]);
    assert.deepEqual(result, [[0.1, 0.2], [0.3, 0.4]]);
  } finally {
    restore();
  }
});

test("embedTexts rejects malformed embedding payloads with a staged error", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    data: [{ embedding: null }]
  }));
  try {
    await assert.rejects(
      () => embedTexts({
        embedding_base_url: "https://api.openai.com/v1",
        embedding_api_key: "sk-test",
        embedding_model: "text-embedding-3-small"
      }, ["eins"]),
      /No embedding vectors/
    );
  } finally {
    restore();
  }
});
