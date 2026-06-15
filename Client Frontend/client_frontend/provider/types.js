import providerCatalog from "../shared/provider_catalog.js";

export const FALLBACK_MODELS = providerCatalog.fallback_models;
export const DEFAULT_BASE_URLS = providerCatalog.default_base_urls;
export const MODEL_CONTEXT_LIMITS = providerCatalog.context_limits;

/**
 * @typedef {{ provider?: string, baseUrl?: string, apiKey?: string }} ModelCatalogRequest
 * @typedef {{ provider?: string, baseUrl: string, apiKey?: string, model: string }} ProviderHealthRequest
 * @typedef {{ llm_provider?: string, llm_base_url: string, llm_api_key?: string, llm_model: string, embedding_provider?: string, embedding_base_url: string, embedding_api_key?: string, embedding_model: string }} ProviderRuntimeConfig
 * @typedef {{ model?: string, temperature?: number, tools?: unknown[] }} ChatCompletionOptions
 */

export class ContextLengthError extends Error {
  constructor(message) {
    super(message);
    this.name = "ContextLengthError";
  }
}
