import { refreshOAuthToken } from "./oauth_flow.js";
import { utcNowIso, writeOAuthReport } from "./oauth_report.js";
import { loadToken, saveToken } from "./oauth_token_store.js";
import { deleteApiKey as deleteStoredApiKey, hasApiKey, loadApiKey, saveApiKey } from "./keystore.js";
import { buildConnectedSession, buildErrorSession, buildLoggedOutSession, providerLabel, providerSettingsForTarget } from "./policy.js";
import { loadCredentialsState, saveCredentialsState } from "./repository.js";
import { OAUTH_REFRESH_SKEW_SECONDS } from "./types.js";
import { expiresWithin, isHealthyOAuthSession } from "./validation.js";

export { finishOAuthLogin, logoutFromOAuth, startOAuthLogin } from "./oauth_session_workflow.js";

async function targetApiKey(stateDir, target, runtimeConfig, providerSettings) {
  const legacyField = target === "embeddings" ? "embedding_api_key" : "llm_api_key";
  const legacyKey = String(runtimeConfig?.[legacyField] || "").trim();
  const storedKey = stateDir ? await loadApiKey(stateDir, target, providerSettings) : "";
  if (!storedKey && legacyKey && stateDir) {
    await saveApiKey(stateDir, target, legacyKey, providerSettings);
  }
  return storedKey || legacyKey;
}

async function targetHasSecret(stateDir, target, runtimeConfig, providerSettings) {
  const legacyField = target === "embeddings" ? "embedding_api_key" : "llm_api_key";
  return Boolean(String(runtimeConfig?.[legacyField] || "").trim())
    || Boolean(stateDir && await hasApiKey(stateDir, target, providerSettings));
}

async function syncTargets(stateDir, state, runtimeConfig) {
  if (!runtimeConfig) {
    return state;
  }
  const llmProvider = providerSettingsForTarget(runtimeConfig, "llm_shared");
  const embeddingProvider = providerSettingsForTarget(runtimeConfig, "embeddings");
  const [llmHasSecret, embeddingHasSecret] = await Promise.all([
    targetHasSecret(stateDir, "llm_shared", runtimeConfig, llmProvider),
    targetHasSecret(stateDir, "embeddings", runtimeConfig, embeddingProvider)
  ]);
  state.targets.llm_shared.has_secret = llmHasSecret;
  state.targets.embeddings.has_secret = embeddingHasSecret;
  return state;
}

function buildTargetState(state, runtimeConfig) {
  const llmProvider = providerSettingsForTarget(runtimeConfig, "llm_shared");
  const embeddingProvider = providerSettingsForTarget(runtimeConfig, "embeddings");
  const oauthSupported = Boolean(llmProvider.oauth_supported);
  const oauthReady = oauthSupported && isHealthyOAuthSession(state.oauth_session);
  const llmHasSecret = Boolean(state.targets.llm_shared.has_secret);
  const embeddingHasSecret = Boolean(state.targets.embeddings.has_secret);
  return {
    auth_mode: oauthReady ? "oauth" : "api_keys",
    oauth_supported: oauthSupported,
    oauth_provider_label: providerLabel(llmProvider),
    oauth_session: state.oauth_session,
    targets: {
      llm_shared: {
        has_secret: llmHasSecret,
        ready: oauthReady || llmHasSecret || llmProvider.api_key_optional,
        source: oauthReady ? "oauth_session" : llmHasSecret ? "llm_api_key" : "",
        fallback_available: llmHasSecret,
        message: oauthReady
          ? state.oauth_session.status_message
          : llmHasSecret
            ? `LLM provider API key for ${providerLabel(llmProvider)} is saved.`
            : llmProvider.api_key_optional
              ? `LLM provider ${providerLabel(llmProvider)} can be used without an API key.`
              : `No LLM provider API key saved for ${providerLabel(llmProvider)}.`
      },
      embeddings: {
        has_secret: embeddingHasSecret,
        ready: embeddingHasSecret || embeddingProvider.api_key_optional,
        source: embeddingHasSecret ? "embedding_api_key" : "",
        fallback_available: false,
        message: embeddingHasSecret
          ? `Embedding provider API key for ${providerLabel(embeddingProvider)} is saved.`
          : embeddingProvider.api_key_optional
            ? `Embedding provider ${providerLabel(embeddingProvider)} can be used without an API key.`
            : `No embedding provider API key saved for ${providerLabel(embeddingProvider)}.`
      }
    }
  };
}

function stateSnapshot(state) {
  return JSON.stringify(state);
}

async function saveResolvedState(stateDir, state, runtimeConfig, previousSnapshot = null) {
  const nextState = await syncTargets(stateDir, state, runtimeConfig);
  if (previousSnapshot === null || stateSnapshot(nextState) !== previousSnapshot) {
    await saveCredentialsState(stateDir, nextState);
  }
  return nextState;
}

export async function resolveCredentialState(stateDir, runtimeConfig, modelCatalogState = null) {
  const state = await loadCredentialsState(stateDir);
  const previousSnapshot = stateSnapshot(state);
  const token = await loadToken(stateDir);
  const llmProvider = providerSettingsForTarget(runtimeConfig, "llm_shared");
  state.oauth_session = token && llmProvider.oauth_supported
    ? buildConnectedSession(token)
    : token
      ? buildConnectedSession(token, `OAuth session is saved, but ${providerLabel(llmProvider)} does not support this OAuth path.`)
    : state.oauth_session.status === "error"
      ? state.oauth_session
      : buildLoggedOutSession();
  const resolved = buildTargetState(await saveResolvedState(stateDir, state, runtimeConfig, previousSnapshot), runtimeConfig);
  return modelCatalogState ? { ...resolved, model_catalog: modelCatalogState } : resolved;
}

export async function resolveLlmRuntime(stateDir, runtimeConfig) {
  const state = await loadCredentialsState(stateDir);
  const previousSnapshot = stateSnapshot(state);
  const llmProvider = providerSettingsForTarget(runtimeConfig, "llm_shared");
  const fallbackKey = await targetApiKey(stateDir, "llm_shared", runtimeConfig, llmProvider);
  let token = await loadToken(stateDir);
  if (token && llmProvider.oauth_supported && expiresWithin(token.expires_at, OAUTH_REFRESH_SKEW_SECONDS)) {
    try {
      token = await refreshOAuthToken(token);
      await saveToken(stateDir, token);
      await writeOAuthReport(stateDir, { event: "refresh", written_at: utcNowIso(), oauth: { token } });
    } catch (error) {
      state.oauth_session = buildErrorSession(`OAuth refresh failed: ${error instanceof Error ? error.message : error}`, state.oauth_session);
      await saveResolvedState(stateDir, state, runtimeConfig, previousSnapshot);
      if (!fallbackKey && !llmProvider.api_key_optional) {
        return { auth_mode: "api_keys", ready: false, error: state.oauth_session.status_message, oauth_session: state.oauth_session };
      }
      return { auth_mode: "api_keys", ready: true, source: "llm_api_key", api_key: fallbackKey, provider_settings: llmProvider, oauth_session: state.oauth_session };
    }
  }
  state.oauth_session = token && llmProvider.oauth_supported
    ? buildConnectedSession(token)
    : token
      ? buildConnectedSession(token, `OAuth session is saved, but ${providerLabel(llmProvider)} does not support this OAuth path.`)
    : state.oauth_session.status === "error"
      ? state.oauth_session
      : buildLoggedOutSession();
  await saveResolvedState(stateDir, state, runtimeConfig, previousSnapshot);
  if (token && llmProvider.oauth_supported) {
    return {
      auth_mode: "oauth",
      ready: true,
      source: "oauth_session",
      provider_settings: llmProvider,
      fallback_api_key: fallbackKey,
      access_token: token.access_token,
      account_id: token.account_id,
      client_id: token.client_id,
      session_id: token.session_id,
      scope: token.scope,
      oauth_session: state.oauth_session
    };
  }
  if (fallbackKey || llmProvider.api_key_optional) {
    return { auth_mode: "api_keys", ready: true, source: "llm_api_key", api_key: fallbackKey, provider_settings: llmProvider, oauth_session: state.oauth_session };
  }
  return { auth_mode: "api_keys", ready: false, error: `No active OAuth login and no LLM provider API key saved for ${providerLabel(llmProvider)}.`, provider_settings: llmProvider, oauth_session: state.oauth_session };
}

export async function resolveTargetApiKey(stateDir, target, runtimeConfig) {
  const providerSettings = providerSettingsForTarget(runtimeConfig, target);
  return await targetApiKey(stateDir, target, runtimeConfig, providerSettings);
}

export async function saveRuntimeApiKeys(stateDir, runtimeConfig) {
  const saved = [];
  for (const [target, field] of [["llm_shared", "llm_api_key"], ["embeddings", "embedding_api_key"]]) {
    const key = String(runtimeConfig?.[field] || "").trim();
    if (!key) continue;
    await saveApiKey(stateDir, target, key, providerSettingsForTarget(runtimeConfig, target));
    saved.push(field);
  }
  return saved;
}

export async function deleteRuntimeApiKey(stateDir, target, runtimeConfig) {
  const providerSettings = providerSettingsForTarget(runtimeConfig, target);
  const deleted = Boolean(stateDir && await deleteStoredApiKey(stateDir, target, providerSettings));
  return {
    deleted,
    provider_settings: providerSettings,
    provider_label: providerLabel(providerSettings)
  };
}
