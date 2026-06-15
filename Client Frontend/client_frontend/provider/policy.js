import { DEFAULT_BASE_URLS, FALLBACK_MODELS, MODEL_CONTEXT_LIMITS } from "./types.js";
import {
  defaultBaseUrlForProvider,
  normalizeProviderId,
  providerApiKeyOptional,
  providerDefinition,
  providerFamily,
  providerModelCatalogStrategy
} from "../shared/provider_catalog.js";

const EMBEDDING_MODEL_PATTERN = /embedding|ada/i;

export function normalizeProvider(provider) {
  return normalizeProviderId(provider);
}

export function defaultBaseUrl(provider) {
  return defaultBaseUrlForProvider(provider) || DEFAULT_BASE_URLS[normalizeProvider(provider)] || "";
}

export function providerRuntime(provider) {
  const provider_id = normalizeProvider(provider);
  const definition = providerDefinition(provider_id);
  return {
    provider_id,
    family: providerFamily(provider_id),
    catalog_strategy: providerModelCatalogStrategy(provider_id),
    api_key_optional: providerApiKeyOptional(provider_id),
    display_name: definition.display_name || provider_id
  };
}

export function getModelContextLimit(modelId) {
  if (!modelId) return null;
  const lower = String(modelId).toLowerCase();
  if (MODEL_CONTEXT_LIMITS[lower]) return MODEL_CONTEXT_LIMITS[lower];
  for (const [key, limit] of Object.entries(MODEL_CONTEXT_LIMITS)) {
    if (lower.startsWith(key)) return limit;
  }
  return null;
}

export function extractModelIds(payload) {
  const rawItems = Array.isArray(payload?.data)
    ? payload.data
    : Array.isArray(payload?.models)
      ? payload.models
      : Array.isArray(payload)
        ? payload
        : [];

  return rawItems.map((item) => {
    if (typeof item === "string") {
      return item.startsWith("models/") ? item.slice(7) : item;
    }
    const modelId = item?.id || item?.name || "";
    return String(modelId).startsWith("models/") ? String(modelId).slice(7) : modelId;
  });
}

export function splitCatalogModels(modelIds) {
  return {
    llmModels: modelIds.filter((model) => !EMBEDDING_MODEL_PATTERN.test(model)),
    embeddingModels: modelIds.filter((model) => EMBEDDING_MODEL_PATTERN.test(model))
  };
}

function buildContextLimits(models) {
  return Object.fromEntries(models.map((model) => [model, getModelContextLimit(model)]));
}

export function buildCatalogResult({ llmModels, embeddingModels, source = "live", error = null }) {
  const finalLlm = llmModels.length ? llmModels : [...FALLBACK_MODELS.llm_models];
  const finalEmbedding = embeddingModels.length ? embeddingModels : [...FALLBACK_MODELS.embedding_models];
  return {
    llm_models: finalLlm,
    embedding_models: finalEmbedding,
    context_limits: buildContextLimits(finalLlm),
    source,
    ...(error ? { error } : {}),
    updated_at: new Date().toISOString()
  };
}

export function buildCatalogFallback(error) {
  return buildCatalogResult({
    llmModels: [...FALLBACK_MODELS.llm_models],
    embeddingModels: [...FALLBACK_MODELS.embedding_models],
    source: "fallback",
    error: error instanceof Error ? error.message : "Model list could not be loaded."
  });
}

export function buildLlmHealthResult(durationMs) {
  return { status: "ok", message: `Connection OK - answer in ${durationMs}ms` };
}

export function buildEmbeddingHealthResult(dimensions) {
  return { status: "ok", message: `Connection OK - ${dimensions} dimensions` };
}
