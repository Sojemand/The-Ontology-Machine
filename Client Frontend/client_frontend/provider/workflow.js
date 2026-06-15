import {
  requestChatCompletion,
  requestEmbeddingHealth,
  requestEmbeddings,
  requestLlmHealth,
  requestModelCatalog
} from "./adapter.js";
import { requestOAuthChatCompletion } from "./oauth_transport.js";
import {
  buildCatalogFallback,
  buildCatalogResult,
  buildEmbeddingHealthResult,
  buildLlmHealthResult,
  extractModelIds,
  splitCatalogModels
} from "./policy.js";
import { resolveEmbeddingRuntime, resolveProviderRuntime, shouldFallbackToApiKey } from "./runtime_auth.js";
import { assertChatChoices, assertEmbeddingDimensions, assertEmbeddingVectors, toCatalogModelIds } from "./validation.js";

export async function fetchModelCatalog(params) {
  try {
    const payload = await requestModelCatalog(params);
    const ids = toCatalogModelIds(extractModelIds(payload));
    return buildCatalogResult(splitCatalogModels(ids));
  } catch (error) {
    return buildCatalogFallback(error);
  }
}

export async function runLlmHealthCheck(params) {
  const startedAt = Date.now();
  assertChatChoices(await requestLlmHealth(params));
  return buildLlmHealthResult(Date.now() - startedAt);
}

export async function runEmbeddingHealthCheck(params) {
  return buildEmbeddingHealthResult(assertEmbeddingDimensions(await requestEmbeddingHealth(params)));
}

export async function createChatCompletion(runtimeConfig, messages, tools) {
  const options = { model: runtimeConfig.llm_model, temperature: 0.2, tools };
  const runtimeAuth = await resolveProviderRuntime(runtimeConfig);
  if (!runtimeAuth.ready) {
    throw new Error(runtimeAuth.error || "LLM provider is not ready.");
  }
  if (runtimeAuth.auth_mode === "oauth" && runtimeAuth.ready) {
    try {
      return await requestOAuthChatCompletion(runtimeAuth, messages, options);
    } catch (error) {
      if (!shouldFallbackToApiKey(runtimeConfig, error, runtimeAuth)) {
        throw error;
      }
      return await requestChatCompletion(runtimeConfig, messages, options, {
        ...runtimeAuth,
        auth_mode: "api_keys",
        api_key: runtimeAuth.fallback_api_key || runtimeAuth.api_key
      });
    }
  }
  return await requestChatCompletion(runtimeConfig, messages, options, runtimeAuth);
}

export async function embedTexts(runtimeConfig, input) {
  const runtimeAuth = await resolveEmbeddingRuntime(runtimeConfig);
  if (!runtimeAuth.ready) {
    throw new Error("Embedding provider is not ready.");
  }
  return assertEmbeddingVectors(await requestEmbeddings({
    provider: runtimeAuth.provider_settings.provider_id,
    baseUrl: runtimeAuth.provider_settings.base_url || runtimeConfig.embedding_base_url,
    apiKey: runtimeAuth.api_key,
    model: runtimeConfig.embedding_model,
    input
  }));
}
