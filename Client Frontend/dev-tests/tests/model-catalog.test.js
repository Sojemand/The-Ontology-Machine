import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { refreshModelCatalogGroup } from "../../client_frontend/model_catalog.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

test("llm model refresh stays on seed/cache when no LLM API key is available", async () => {
  const stateDir = mkdtempSync(path.join(os.tmpdir(), "vp-model-catalog-"));
  try {
    const result = await refreshModelCatalogGroup(
      stateDir,
      { llm_model: "gpt-5.4", embedding_model: "text-embedding-3-small" },
      { group: "llm_shared", provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "" }
    );
    assert.equal(result.source, "seed");
    assert.equal(
      result.error,
      "OpenAI OAuth active; live model list requires an API key, using cache/seed for LLM catalogs."
    );
    assert.deepEqual(result.llm_models, [
      "gpt-5.4",
      "gpt-5.5-pro",
      "gpt-5.5",
      "gpt-5.5-mini",
      "gpt-5.5-nano",
      "gpt-5.4-pro",
      "gpt-5.4-mini",
      "gpt-5.4-nano",
      "gpt-5.2-pro",
      "gpt-5.2",
      "gpt-5.2-mini",
      "gpt-5.2-nano",
      "gpt-5.1",
      "gpt-5.1-mini",
      "gpt-5.1-nano",
      "gpt-5-pro",
      "gpt-5",
      "gpt-5-chat-latest",
      "gpt-5-mini",
      "gpt-5-nano"
    ]);
  } finally {
    rmSync(stateDir, { recursive: true, force: true });
  }
});

test("frontend_policy source order can prefer fallback over seed", async () => {
  const stateDir = mkdtempSync(path.join(os.tmpdir(), "vp-model-catalog-"));
  try {
    const frontendPolicy = buildDefaultFrontendPolicy();
    frontendPolicy.model_catalog.llm_source_order = ["live", "fallback", "seed", "cache"];
    const result = await refreshModelCatalogGroup(
      stateDir,
      { llm_model: "gpt-5.4", embedding_model: "text-embedding-3-small" },
      frontendPolicy,
      { group: "llm_shared", provider: "openai", baseUrl: "https://api.openai.com/v1", apiKey: "" }
    );
    assert.equal(result.source, "fallback");
    assert.equal(result.llm_models[0], "gpt-5.5-pro");
  } finally {
    rmSync(stateDir, { recursive: true, force: true });
  }
});
