export const MODEL_CATALOG_STATE_FILE = "model_catalog_state.json";
const LEGACY_OPENAI_PROVIDER_ID = "openai";
const LEGACY_OPENAI_BASE_URL = "https://api.openai.com/v1";

export function buildEmptyGroup(models = [], source = "seed", refreshedAt = "", providerId = "", baseUrl = "") {
  return {
    models: Array.from(new Set((Array.isArray(models) ? models : []).map((value) => String(value || "").trim()).filter(Boolean))),
    refreshed_at: String(refreshedAt || ""),
    source: String(source || "seed"),
    provider_id: String(providerId || "").trim(),
    base_url: String(baseUrl || "").trim().replace(/\/+$/, "")
  };
}

export function groupMatchesProvider(group, providerSettings = {}) {
  const groupProviderId = String(group?.provider_id || "").trim();
  const groupBaseUrl = String(group?.base_url || "").trim().replace(/\/+$/, "");
  const providerId = String(providerSettings.provider_id || providerSettings.provider || "").trim();
  const baseUrl = String(providerSettings.base_url || providerSettings.baseUrl || "").trim().replace(/\/+$/, "");
  if (!groupProviderId && !groupBaseUrl) {
    return providerId === LEGACY_OPENAI_PROVIDER_ID && baseUrl === LEGACY_OPENAI_BASE_URL;
  }
  return groupProviderId === providerId && groupBaseUrl === baseUrl;
}

function groupKey(group) {
  return [String(group?.provider_id || "").trim(), String(group?.base_url || "").trim().replace(/\/+$/, "")].join("|");
}

function hasPayload(group) {
  return Boolean(group?.models?.length || group?.refreshed_at || group?.source || group?.provider_id || group?.base_url);
}

export function groupsFor(state, target) {
  const current = state?.[target] || buildEmptyGroup();
  const catalogs = target === "embeddings" ? state?.embeddings_catalogs : state?.llm_shared_catalogs;
  const merged = [];
  const seen = new Set();
  for (const group of [current, ...(Array.isArray(catalogs) ? catalogs : [])]) {
    if (!hasPayload(group)) continue;
    const key = groupKey(group);
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(group);
  }
  return merged;
}

export function groupFor(state, target, providerSettings = null) {
  const current = state?.[target] || buildEmptyGroup();
  if (!providerSettings || groupMatchesProvider(current, providerSettings)) return current;
  return groupsFor(state, target).find((group) => groupMatchesProvider(group, providerSettings)) || buildEmptyGroup();
}

export function replaceGroup(state, target, group) {
  const nextState = { ...state };
  const catalogsKey = target === "embeddings" ? "embeddings_catalogs" : "llm_shared_catalogs";
  const key = groupKey(group);
  const catalogs = groupsFor(state, target).filter((existing) => groupKey(existing) !== key);
  if (hasPayload(group)) catalogs.unshift(group);
  nextState[target] = group;
  nextState[catalogsKey] = catalogs;
  return nextState;
}
