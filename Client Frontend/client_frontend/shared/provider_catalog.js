import providerCatalog from "../../shared/provider-catalog.json" with { type: "json" };

const providers = Array.isArray(providerCatalog.providers) ? providerCatalog.providers : [];
const providersById = new Map(providers.map((provider) => [provider.provider_id, provider]));
const aliases = new Map();

for (const provider of providers) {
  aliases.set(String(provider.provider_id || "").toLowerCase(), provider.provider_id);
  aliases.set(String(provider.display_name || "").trim().toLowerCase(), provider.provider_id);
  for (const alias of provider.aliases || []) {
    aliases.set(String(alias || "").trim().toLowerCase(), provider.provider_id);
  }
}

export function normalizeProviderId(value, defaultProvider = "openai") {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) {
    return providersById.has(defaultProvider) ? defaultProvider : providers[0]?.provider_id || "";
  }
  return aliases.get(raw) || (providersById.has(raw) ? raw : "openai_compat");
}

export function providerDefinition(value, defaultProvider = "openai") {
  const providerId = normalizeProviderId(value, defaultProvider);
  return providersById.get(providerId) || providersById.get("openai_compat") || providers[0] || {};
}

export function providersForTarget(target) {
  const key = target === "embeddings" || target === "embedding" ? "embeddings_enabled" : "llm_enabled";
  return providers.filter((provider) => provider[key]);
}

export function providerIdsForTarget(target) {
  return providersForTarget(target).map((provider) => provider.provider_id);
}

export function providerDisplayName(value) {
  return providerDefinition(value).display_name || String(value || "");
}

export function providerIdForDisplayName(value, target, defaultProvider = "openai") {
  const providerId = normalizeProviderId(value, defaultProvider);
  return providerIdsForTarget(target).includes(providerId)
    ? providerId
    : providersForTarget(target)[0]?.provider_id || defaultProvider;
}

export function defaultBaseUrlForProvider(value) {
  const definition = providerDefinition(value);
  return definition.default_base_url || providerCatalog.default_base_urls?.[definition.provider_id] || "";
}

export function providerFamily(value) {
  return providerDefinition(value).family || "openai_chat";
}

export function providerModelCatalogStrategy(value) {
  return providerDefinition(value).model_catalog_strategy || "openai";
}

export function providerApiKeyOptional(value) {
  return Boolean(providerDefinition(value).api_key_optional);
}

export function providerOAuthSupported(value) {
  return Boolean(providerDefinition(value).oauth_supported);
}

export default providerCatalog;
