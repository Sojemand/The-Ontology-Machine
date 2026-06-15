import { fetchModelCatalog, getModelContextLimit } from "../provider.js";
import { resolveModelCatalogPolicy } from "../frontend_policy.js";
import providerCatalog from "../shared/provider_catalog.js";
import { providerApiKeyOptional } from "../shared/provider_catalog.js";
import { providerSettingsForTarget } from "../credentials/policy.js";
import { loadStoredModelCatalogState, saveModelCatalogState } from "./repository.js";
import { buildEmptyGroup, groupFor, replaceGroup } from "./types.js";

function dedupe(values = []) {
  return Array.from(new Set((Array.isArray(values) ? values : []).map((value) => String(value || "").trim()).filter(Boolean)));
}

function buildGroupPolicy(runtimeConfig, frontendPolicy) {
  const policy = resolveModelCatalogPolicy(frontendPolicy);
  return {
    llm_shared: {
      seed: dedupe([runtimeConfig?.llm_model || "", ...policy.llm_seed_models]),
      fallback: dedupe(providerCatalog.fallback_models.llm_models),
      order: policy.llm_source_order
    },
    embeddings: {
      seed: dedupe([runtimeConfig?.embedding_model || "", ...policy.embedding_seed_models]),
      fallback: dedupe(providerCatalog.fallback_models.embedding_models),
      order: policy.embedding_source_order
    }
  };
}

function resolveDisplayGroup(stored, target, policyGroup, providerSettings) {
  const storedGroup = groupFor(stored, target, providerSettings);
  const candidates = {
    cache: storedGroup.models.length && (storedGroup.source === "live" || storedGroup.source === "cache")
      ? buildEmptyGroup(storedGroup.models, "cache", storedGroup.refreshed_at)
      : null,
    seed: buildEmptyGroup(policyGroup.seed, "seed"),
    fallback: buildEmptyGroup(policyGroup.fallback, "fallback")
  };
  for (const source of policyGroup.order) {
    if (source !== "live" && candidates[source]?.models.length) {
      return candidates[source];
    }
  }
  return candidates.seed;
}

function resolveDisplayState(stored, runtimeConfig, frontendPolicy) {
  const policy = buildGroupPolicy(runtimeConfig, frontendPolicy);
  const llmProvider = providerSettingsForTarget(runtimeConfig, "llm_shared");
  const embeddingProvider = providerSettingsForTarget(runtimeConfig, "embeddings");
  return {
    llm_shared: resolveDisplayGroup(stored, "llm_shared", policy.llm_shared, llmProvider),
    embeddings: resolveDisplayGroup(stored, "embeddings", policy.embeddings, embeddingProvider)
  };
}

function buildResponse(state, source, error = "") {
  return {
    llm_models: [...state.llm_shared.models],
    embedding_models: [...state.embeddings.models],
    context_limits: Object.fromEntries(state.llm_shared.models.map((model) => [model, getModelContextLimit(model)])),
    source,
    ...(error ? { error } : {}),
    updated_at: new Date().toISOString()
  };
}

function buildCachedResponse(state, group, error = "") {
  const source = state[group].source || "seed";
  return buildResponse(state, source, error);
}

export async function loadModelCatalogState(stateDir, runtimeConfig, frontendPolicy) {
  const stored = await loadStoredModelCatalogState(stateDir);
  return resolveDisplayState(stored, runtimeConfig, frontendPolicy);
}

export async function refreshModelCatalog(stateDir, runtimeConfig, frontendPolicy, request) {
  const group = request?.group === "embeddings" ? "embeddings" : "llm_shared";
  const stored = await loadStoredModelCatalogState(stateDir);
  const current = resolveDisplayState(stored, runtimeConfig, frontendPolicy);
  const providerSettings = {
    provider_id: request?.provider || providerSettingsForTarget(runtimeConfig, group).provider_id,
    base_url: request?.baseUrl || providerSettingsForTarget(runtimeConfig, group).base_url
  };
  if (!request?.apiKey && !providerApiKeyOptional(providerSettings.provider_id)) {
    const message =
      group === "llm_shared"
        ? "OpenAI OAuth active; live model list requires an API key, using cache/seed for LLM catalogs."
        : "Embedding model list requires an API key, using cache/seed.";
    return buildCachedResponse(current, group, message);
  }
  const live = await fetchModelCatalog({
    provider: request.provider,
    baseUrl: request.baseUrl,
    apiKey: request.apiKey
  });
  if (live.source !== "live") {
    return buildCachedResponse(current, group, live.error || "Model list could not be loaded.");
  }
  const nextGroup = group === "llm_shared"
    ? buildEmptyGroup(live.llm_models, "live", live.updated_at, providerSettings.provider_id, providerSettings.base_url)
    : buildEmptyGroup(live.embedding_models, "live", live.updated_at, providerSettings.provider_id, providerSettings.base_url);
  const nextStored = replaceGroup(stored, group, nextGroup);
  await saveModelCatalogState(stateDir, nextStored);
  const nextState = resolveDisplayState(nextStored, runtimeConfig, frontendPolicy);
  nextState[group] = nextGroup;
  return buildResponse(nextState, "live");
}
