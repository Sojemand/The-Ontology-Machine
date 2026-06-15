import { estimateMemoryTurns } from "../min_agent.js";
import { normalizeTokenUsage } from "../token_usage.js";

function refreshSource(source, sourceResolver) {
  const sourceId = String(source?.id || "").trim();
  if (!sourceId || typeof sourceResolver !== "function") {
    return source;
  }
  try {
    return sourceResolver(sourceId) || source;
  } catch {
    return source;
  }
}

function toPublicSource(source, sourceResolver = null) {
  const refreshedSource = refreshSource(source, sourceResolver);
  if (!source || typeof source !== "object") {
    return null;
  }
  const sourceId = String(refreshedSource?.id || source.id || "").trim();
  if (!sourceId) {
    return null;
  }
  return {
    id: sourceId,
    source_key: String(refreshedSource.source_key || source.source_key || sourceId),
    title: String(refreshedSource.title || source.title || sourceId),
    type: refreshedSource.type || source.type || null,
    date: refreshedSource.date || source.date || null,
    actor: refreshedSource.actor || source.actor || null,
    source_page: refreshedSource.source_page || source.source_page || null,
    source_page_count: refreshedSource.source_page_count || source.source_page_count || null,
    page: Math.max(1, Number(refreshedSource.page ?? source.page) || 1),
    page_count: Math.max(1, Number(refreshedSource.page_count ?? source.page_count) || 1),
    source_refs: Array.isArray(source.source_refs) ? source.source_refs.filter(Boolean) : [],
    snippet: String(refreshedSource.snippet || source.snippet || ""),
    image_url: String(refreshedSource.image_url || source.image_url || `/api/image/${encodeURIComponent(sourceId)}/1`),
    viewer_available: Boolean(refreshedSource.viewer_available ?? source.viewer_available),
    file_name: refreshedSource.file_name ? String(refreshedSource.file_name) : source.file_name ? String(source.file_name) : undefined
  };
}

export function toPublicSources(sources, sourceResolver = null) {
  const publicSources = [];
  const seen = new Set();
  for (const source of Array.isArray(sources) ? sources : []) {
    const publicSource = toPublicSource(source, sourceResolver);
    const key = String(publicSource?.source_key || publicSource?.id || "").trim();
    if (!publicSource || !key || seen.has(key)) continue;
    seen.add(key);
    publicSources.push(publicSource);
  }
  return publicSources;
}

export function toPublicChatMessage(message, sourceResolver = null) {
  return {
    role: message.role,
    content: message.content,
    sources: toPublicSources(message.sources, sourceResolver),
    mode: message.mode,
    exactness: message.exactness,
    metrics: message.metrics,
    ambiguities: message.ambiguities,
    method: message.method,
    token_usage: message.token_usage ? normalizeTokenUsage(message.token_usage) : undefined
  };
}

export function normalizeChatResult(result, history, message) {
  const answer = result?.answer || "I could not formulate a reliable answer.";
  const trimmedMessage = String(message || "").trim();
  return {
    answer,
    sources: toPublicSources(result?.sources),
    history: Array.isArray(result?.history)
      ? result.history
      : [...(Array.isArray(history) ? history : []), { role: "user", content: trimmedMessage }, { role: "assistant", content: answer }],
    mode: result?.mode,
    exactness: result?.exactness,
    metrics: result?.metrics,
    ambiguities: result?.ambiguities,
    method: result?.method,
    token_usage: result?.token_usage ? normalizeTokenUsage(result.token_usage) : undefined
  };
}

export function buildDisplayMessages(userMessage, result) {
  return [
    { role: "user", content: userMessage },
    {
      role: "assistant",
      content: result.answer,
      sources: result.sources,
      mode: result.mode,
      exactness: result.exactness,
      method: result.method,
      metrics: result.metrics,
      ambiguities: result.ambiguities,
      token_usage: result.token_usage
    }
  ];
}

export function getChatTitle(messages) {
  return messages.find((message) => message?.role === "user")?.content || "";
}

export function buildChatPayload(result) {
  return {
    answer: result.answer,
    sources: result.sources,
    mode: result.mode,
    exactness: result.exactness,
    metrics: result.metrics,
    ambiguities: result.ambiguities,
    method: result.method,
    token_usage: result.token_usage
  };
}

export function buildHealthPayload(context) {
  const config = context.getConfig();
  const contextLimit = config.context_limit || 127_096;
  const databaseStatus = typeof context.agent.databaseStatus === "function"
    ? context.agent.databaseStatus()
    : {
        base_graph: { available: false },
        ontology_lenses: { available: false, count: 0 }
      };
  return {
    status: "ok",
    corpus_docs: context.agent.countDocuments(),
    llm_model: config.llm_model,
    customer_name: config.customer_name,
    agent_name: context.agentName,
    theme: config.theme,
    llm_ready: false,
    embedding_ready: false,
    database_status: databaseStatus,
    context_limit: contextLimit,
    memory_turns: estimateMemoryTurns(contextLimit, context.getFrontendPolicy?.())
  };
}

export function buildProtectedConfig(config, frontendPolicy, frontendPolicyDiagnostics, isProtected, credentialState) {
  const masked = getMaskedConfigShape(config);
  if (credentialState?.targets?.llm_shared?.has_secret) masked.llm_api_key = "configured";
  if (credentialState?.targets?.embeddings?.has_secret) masked.embedding_api_key = "configured";
  return {
    ...masked,
    frontend_policy: frontendPolicy,
    ...(frontendPolicyDiagnostics ? { frontend_policy_diagnostics: frontendPolicyDiagnostics } : {}),
    protected: Boolean(isProtected),
    credential_state: credentialState
  };
}

export function buildLlmHealthPayload(body, config, runtimeConfig, defaultBaseUrl) {
  const provider = body.provider || config.llm_provider;
  return {
    provider,
    baseUrl: body.base_url || config.llm_base_url || defaultBaseUrl(provider),
    apiKey: body.api_key || runtimeConfig.llm_api_key,
    model: body.model || config.llm_model
  };
}

export function buildEmbeddingHealthPayload(body, config, runtimeConfig, defaultBaseUrl) {
  const provider = body.provider || config.embedding_provider;
  return {
    provider,
    baseUrl: body.base_url || config.embedding_base_url || defaultBaseUrl(provider),
    apiKey: body.api_key || runtimeConfig.embedding_api_key,
    model: body.model || config.embedding_model
  };
}

export function buildModelCatalogPayload(body, config, runtimeConfig) {
  const group = body.group === "embeddings" ? "embeddings" : "llm_shared";
  return {
    group,
    provider: body.provider || (group === "embeddings" ? config.embedding_provider : config.llm_provider),
    baseUrl: body.base_url || (group === "embeddings" ? config.embedding_base_url : config.llm_base_url),
    apiKey: body.api_key || (group === "embeddings" ? runtimeConfig.embedding_api_key : runtimeConfig.llm_api_key)
  };
}

function getMaskedConfigShape(config) {
  return {
    ...config,
    llm_api_key: config.llm_api_key ? "configured" : "",
    embedding_api_key: config.embedding_api_key ? "configured" : "",
    admin_secret: config.admin_secret ? "configured" : ""
  };
}
