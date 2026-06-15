import { getLlmRuntime, getTargetApiKey } from "../credentials.js";
import { providerSettingsForTarget } from "../credentials/policy.js";

export async function resolveProviderRuntime(runtimeConfig) {
  if (!runtimeConfig?.state_dir) {
    const providerSettings = providerSettingsForTarget(runtimeConfig, "llm_shared");
    return {
      auth_mode: "api_keys",
      ready: Boolean(String(runtimeConfig?.llm_api_key || "").trim()) || providerSettings.api_key_optional,
      source: "llm_api_key",
      api_key: String(runtimeConfig?.llm_api_key || "").trim(),
      provider_settings: providerSettings
    };
  }
  return await getLlmRuntime(runtimeConfig.state_dir, runtimeConfig);
}

export async function resolveEmbeddingRuntime(runtimeConfig) {
  const providerSettings = providerSettingsForTarget(runtimeConfig, "embeddings");
  const apiKey = runtimeConfig?.state_dir
    ? await getTargetApiKey(runtimeConfig.state_dir, "embeddings", runtimeConfig)
    : String(runtimeConfig?.embedding_api_key || "").trim();
  return {
    ready: Boolean(apiKey) || providerSettings.api_key_optional,
    api_key: apiKey,
    provider_settings: providerSettings
  };
}

export function shouldFallbackToApiKey(runtimeConfig, error, runtimeAuth = {}) {
  if (!String(runtimeAuth.fallback_api_key || runtimeAuth.api_key || runtimeConfig?.llm_api_key || "").trim()) {
    return false;
  }
  const message = error instanceof Error ? error.message : String(error || "");
  return /oauth|401|unauthorized|backend/i.test(message);
}
