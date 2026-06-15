import assert from "node:assert/strict";
import test from "node:test";

import { createConfigApp } from "../../src/config_app.ts";
import { createApi, createConfig, createDom, createModelsResponse, deferred, optionValues } from "./config-app-test-fixtures.js";

test("boot keeps LLM and embedding model catalogs isolated per section", async () => {
  const dom = createDom();
  const api = createApi({
    getCurrentConfig: async () => createConfig({
      llm_provider: "openai",
      llm_model: "gpt-4.1",
      embedding_provider: "mammouth",
      embedding_model: "mammouth-embed"
    }),
    getModels: async (params) => params.provider === "mammouth"
      ? createModelsResponse({
        llm_models: ["mammouth-chat"],
        embedding_models: ["mammouth-embed", "mammouth-embed-plus"],
        context_limits: { "mammouth-chat": 64000 }
      })
      : createModelsResponse({
        llm_models: ["gpt-4.1", "gpt-4o"],
        embedding_models: ["text-embedding-3-small"]
      })
  });
  const app = createConfigApp({ api, document: dom.window.document });

  await app.boot();

  const llmSelect = dom.window.document.querySelector("#llm-model");
  const embeddingSelect = dom.window.document.querySelector("#embedding-model");
  assert.deepEqual(optionValues(llmSelect), ["gpt-4.1", "gpt-4o"]);
  assert.deepEqual(optionValues(embeddingSelect), ["mammouth-embed", "mammouth-embed-plus"]);
  assert.equal(llmSelect.value, "gpt-4.1");
  assert.equal(embeddingSelect.value, "mammouth-embed");
});

test("refreshing embedding models keeps unsaved LLM selection and options intact", async () => {
  const dom = createDom();
  const api = createApi({
    getModels: async (params) => params.provider === "mammouth"
      ? createModelsResponse({ llm_models: ["mammouth-chat"], embedding_models: ["mammouth-embed", "mammouth-embed-plus"] })
      : createModelsResponse({ llm_models: ["gpt-4.1", "gpt-4o-mini"], embedding_models: ["text-embedding-3-small", "text-embedding-3-large"] })
  });
  const app = createConfigApp({ api, document: dom.window.document });

  await app.boot();

  const llmSelect = dom.window.document.querySelector("#llm-model");
  const embeddingSelect = dom.window.document.querySelector("#embedding-model");
  llmSelect.value = "gpt-4o-mini";
  embeddingSelect.value = "text-embedding-3-large";

  dom.window.document.querySelector('input[name="embedding_provider"][value="mammouth"]').checked = true;
  await app.refreshModels("embedding");

  assert.deepEqual(optionValues(llmSelect), ["gpt-4.1", "gpt-4o-mini"]);
  assert.equal(llmSelect.value, "gpt-4o-mini");
  assert.deepEqual(optionValues(embeddingSelect), ["mammouth-embed", "mammouth-embed-plus"]);
});

test("stale model catalog responses no longer overwrite the latest section state", async () => {
  const dom = createDom();
  const api = createApi();
  const app = createConfigApp({ api, document: dom.window.document });
  const first = deferred();
  const second = deferred();
  let callCount = 0;

  await app.boot();

  api.getModels = async () => {
    callCount += 1;
    return callCount === 1 ? first.promise : second.promise;
  };

  const firstRefresh = app.refreshModels("llm");
  const secondRefresh = app.refreshModels("llm");

  second.resolve(createModelsResponse({ llm_models: ["gpt-5-fast", "gpt-5-mini"], context_limits: { "gpt-5-fast": 256000, "gpt-5-mini": 128000 } }));
  await secondRefresh;

  const llmSelect = dom.window.document.querySelector("#llm-model");
  assert.deepEqual(optionValues(llmSelect), ["gpt-5-fast", "gpt-5-mini"]);

  first.resolve(createModelsResponse({ llm_models: ["gpt-stale"], context_limits: { "gpt-stale": 32000 } }));
  await firstRefresh;

  assert.deepEqual(optionValues(llmSelect), ["gpt-5-fast", "gpt-5-mini"]);
  assert.deepEqual(app.getState().llmModels, ["gpt-5-fast", "gpt-5-mini"]);
});
