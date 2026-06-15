import { defaultBaseUrl, normalizeProvider, providerRuntime } from "./policy.js";
import { buildJsonHeaders, requestJson, trimBaseUrl } from "./adapter_core.js";
import { ANTHROPIC_VERSION, anthropicBody, normalizeAnthropicPayload } from "./adapter_anthropic.js";
import { googleBody, googleEmbeddingRequests, normalizeGooglePayload } from "./adapter_google.js";
import { normalizeResponsesPayload, openAiChatBody, responsesBody } from "./adapter_openai.js";

function assertKey(provider, apiKey, optional) {
  if (!apiKey && !optional) throw new Error(`[provider:${provider}] API key is missing.`);
}

export async function requestModelCatalog({ provider, baseUrl, apiKey }) {
  const providerId = normalizeProvider(provider);
  const runtime = providerRuntime(providerId);
  const normalizedBaseUrl = trimBaseUrl(baseUrl || defaultBaseUrl(providerId));
  if (runtime.catalog_strategy === "anthropic") {
    assertKey("model_catalog", apiKey, false);
    return await requestJson("model_catalog", `${normalizedBaseUrl}/models`, { method: "GET", headers: { "x-api-key": apiKey, "anthropic-version": ANTHROPIC_VERSION } });
  }
  if (runtime.catalog_strategy === "google") {
    assertKey("model_catalog", apiKey, false);
    return await requestJson("model_catalog", `${normalizedBaseUrl}/models?${new URLSearchParams({ key: apiKey })}`, { method: "GET" });
  }
  const endpoint = runtime.catalog_strategy === "mammouth" ? `${new URL(normalizedBaseUrl).origin}/public/models` : `${normalizedBaseUrl}/models`;
  assertKey("model_catalog", apiKey, runtime.api_key_optional || runtime.catalog_strategy === "mammouth");
  return await requestJson("model_catalog", endpoint, { method: "GET", headers: buildJsonHeaders(apiKey) });
}

export async function requestLlmHealth(params) {
  return await requestChatByProvider({ provider: params.provider, baseUrl: params.baseUrl, apiKey: params.apiKey, model: params.model }, [{ role: "user", content: "Hallo" }], { model: params.model, temperature: 0.2 });
}

export async function requestEmbeddingHealth(params) {
  return await requestEmbeddings({ provider: params.provider, baseUrl: params.baseUrl, apiKey: params.apiKey, model: params.model, input: "test" });
}

export async function requestChatCompletion(runtimeConfig, messages, options = {}, runtimeAuth = {}) {
  const provider = runtimeConfig.llm_provider || (runtimeAuth.auth_mode === "oauth" ? runtimeAuth.provider_settings?.provider_id : "");
  return await requestChatByProvider({
    provider,
    baseUrl: runtimeAuth.provider_settings?.base_url || runtimeConfig.llm_base_url,
    apiKey: runtimeAuth.api_key ?? runtimeConfig.llm_api_key,
    model: options.model || runtimeConfig.llm_model
  }, messages, options);
}

async function requestChatByProvider({ provider, baseUrl, apiKey, model }, messages, options = {}) {
  const providerProvided = Boolean(String(provider || "").trim());
  const providerId = normalizeProvider(provider);
  const runtime = providerRuntime(providerId);
  const normalizedBaseUrl = trimBaseUrl(baseUrl || defaultBaseUrl(providerId));
  assertKey("chat_completion", apiKey, runtime.api_key_optional);
  if (runtime.family === "anthropic_messages") return await requestAnthropicChat(normalizedBaseUrl, apiKey, messages, { ...options, model });
  if (runtime.family === "google_gemini") return await requestGoogleChat(normalizedBaseUrl, apiKey, model, messages, options);
  if (runtime.family === "openai_responses" && providerProvided) return await requestResponsesChat(normalizedBaseUrl, apiKey, messages, { ...options, model });
  return await requestJson("chat_completion", `${normalizedBaseUrl}/chat/completions`, {
    method: "POST",
    headers: buildJsonHeaders(apiKey),
    body: JSON.stringify(openAiChatBody(messages, {
      ...options,
      model,
      toolChoice: chatToolChoice(providerId, options)
    }))
  });
}

function chatToolChoice(providerId, options = {}) {
  if (!Array.isArray(options.tools) || !options.tools.length) return undefined;
  if (options.toolChoice || options.tool_choice) return options.toolChoice || options.tool_choice;
  return "auto";
}

export async function requestEmbeddings({ provider, baseUrl, apiKey, model, input }) {
  const providerId = normalizeProvider(provider);
  const runtime = providerRuntime(providerId);
  const normalizedBaseUrl = trimBaseUrl(baseUrl || defaultBaseUrl(providerId));
  assertKey("embedding_request", apiKey, runtime.api_key_optional);
  if (runtime.family === "google_gemini") return await requestGoogleEmbeddings(normalizedBaseUrl, apiKey, model, input);
  if (runtime.family === "anthropic_messages") throw new Error("[provider:embedding_request] Anthropic does not provide embeddings in this profile.");
  return await requestJson("embedding_request", `${normalizedBaseUrl}/embeddings`, {
    method: "POST",
    headers: buildJsonHeaders(apiKey),
    body: JSON.stringify({ model, input })
  });
}

async function requestAnthropicChat(baseUrl, apiKey, messages, options) {
  const payload = await requestJson("chat_completion", `${baseUrl}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": apiKey, "anthropic-version": ANTHROPIC_VERSION },
    body: JSON.stringify(anthropicBody(messages, options))
  });
  return normalizeAnthropicPayload(payload);
}

async function requestGoogleChat(baseUrl, apiKey, model, messages, options) {
  const modelId = normalizeGoogleModel(model);
  const payload = await requestJson("chat_completion", `${baseUrl}/models/${encodeURIComponent(modelId)}:generateContent?${new URLSearchParams({ key: apiKey })}`, {
    method: "POST",
    headers: buildJsonHeaders(""),
    body: JSON.stringify(googleBody(messages, { ...options, model: modelId }))
  });
  return normalizeGooglePayload(payload);
}

async function requestResponsesChat(baseUrl, apiKey, messages, options) {
  const payload = await requestJson("chat_completion", `${baseUrl}/responses`, {
    method: "POST",
    headers: buildJsonHeaders(apiKey),
    body: JSON.stringify(responsesBody(messages, options))
  });
  return normalizeResponsesPayload(payload);
}

async function requestGoogleEmbeddings(baseUrl, apiKey, model, input) {
  const modelId = normalizeGoogleModel(model);
  const payload = await requestJson("embedding_request", `${baseUrl}/models/${encodeURIComponent(modelId)}:batchEmbedContents?${new URLSearchParams({ key: apiKey })}`, {
    method: "POST",
    headers: buildJsonHeaders(""),
    body: JSON.stringify({ requests: googleEmbeddingRequests(modelId, input) })
  });
  return { data: (payload.embeddings || []).map((embedding) => ({ embedding: embedding.values || [] })) };
}

function normalizeGoogleModel(model) {
  return String(model || "").startsWith("models/") ? String(model).slice(7) : model;
}
