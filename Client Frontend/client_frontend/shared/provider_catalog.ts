import providerCatalog from "../../shared/provider-catalog.json" with { type: "json" };

type ProviderDefinition = {
  provider_id: string;
  display_name: string;
  family: string;
  default_base_url: string;
  llm_enabled?: boolean;
  embeddings_enabled?: boolean;
  api_key_optional?: boolean;
  oauth_supported?: boolean;
  model_catalog_strategy?: string;
  aliases?: string[];
};

const providers = (Array.isArray((providerCatalog as { providers?: ProviderDefinition[] }).providers)
  ? (providerCatalog as { providers: ProviderDefinition[] }).providers
  : []) as ProviderDefinition[];
const providersById = new Map(providers.map((provider) => [provider.provider_id, provider]));
const aliases = new Map<string, string>();

for (const provider of providers) {
  aliases.set(String(provider.provider_id || "").toLowerCase(), provider.provider_id);
  aliases.set(String(provider.display_name || "").trim().toLowerCase(), provider.provider_id);
  for (const alias of provider.aliases || []) {
    aliases.set(String(alias || "").trim().toLowerCase(), provider.provider_id);
  }
}

export function normalizeProviderId(value: unknown, defaultProvider = "openai"): string {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) {
    return providersById.has(defaultProvider) ? defaultProvider : providers[0]?.provider_id || "";
  }
  return aliases.get(raw) || (providersById.has(raw) ? raw : "openai_compat");
}

export function providerDefinition(value: unknown, defaultProvider = "openai"): ProviderDefinition {
  const providerId = normalizeProviderId(value, defaultProvider);
  return providersById.get(providerId) || providersById.get("openai_compat") || providers[0] || ({} as ProviderDefinition);
}

export function providersForTarget(target: string): ProviderDefinition[] {
  const key = target === "embeddings" || target === "embedding" ? "embeddings_enabled" : "llm_enabled";
  return providers.filter((provider) => Boolean(provider[key as keyof ProviderDefinition]));
}

export function providerIdsForTarget(target: string): string[] {
  return providersForTarget(target).map((provider) => provider.provider_id);
}

export function providerDisplayName(value: unknown): string {
  return providerDefinition(value).display_name || String(value || "");
}

export function providerIdForDisplayName(value: unknown, target: string, defaultProvider = "openai"): string {
  const providerId = normalizeProviderId(value, defaultProvider);
  return providerIdsForTarget(target).includes(providerId)
    ? providerId
    : providersForTarget(target)[0]?.provider_id || defaultProvider;
}

export function defaultBaseUrlForProvider(value: unknown): string {
  const definition = providerDefinition(value);
  const catalog = providerCatalog as { default_base_urls?: Record<string, string> };
  return definition.default_base_url || catalog.default_base_urls?.[definition.provider_id] || "";
}

export function providerOAuthSupported(value: unknown): boolean {
  return Boolean(providerDefinition(value).oauth_supported);
}

export default providerCatalog;
