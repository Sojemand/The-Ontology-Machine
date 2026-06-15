import { assertSqlDatabaseAccessible, SqlDatabasePathError, normalizeStoredSqlDatabasePath } from "../config/database_path.js";
import { saveConfigState } from "../config.js";
import { deleteTargetApiKey, getTargetApiKey, persistRuntimeApiKeys } from "../credentials.js";
import { FrontendPolicyValidationError } from "../frontend_policy/validation.js";
import { refreshModelCatalogGroup } from "../model_catalog.js";
import { defaultBaseUrl, runEmbeddingHealthCheck, runLlmHealthCheck } from "../provider.js";
import { getAdminTokenFromCookies, json, parseCookies, readJsonBody, setAdminCookie } from "./adapter.js";
import { buildEmbeddingHealthPayload, buildLlmHealthPayload, buildModelCatalogPayload } from "./policy.js";

function requireAdminSession(context, request, response) {
  const runtimeConfig = context.getRuntimeConfig();
  const token = getAdminTokenFromCookies(context.vaultDir, parseCookies(request.headers.cookie));
  if (context.adminSessions.has(token, runtimeConfig.admin_secret)) {
    return runtimeConfig;
  }
  json(response, 403, { error: "Admin unlock required." });
  return null;
}

async function handleCurrentConfigRoute({ response, context }) {
  json(response, 200, await context.getProtectedConfig());
}

async function handleUnlockConfigRoute({ request, response, context }) {
  const secret = String((await readJsonBody(request)).secret || "").trim();
  if (!context.getRuntimeConfig().admin_secret || secret !== context.getRuntimeConfig().admin_secret) {
    json(response, 403, { error: "Wrong admin password." });
    return;
  }
  setAdminCookie(context.vaultDir, response, context.adminSessions.create(context.getRuntimeConfig().admin_secret), request);
  json(response, 200, { status: "ok" });
}

function pickNextSqlDatabasePath(currentConfig, body) {
  if (body && typeof body === "object" && Object.prototype.hasOwnProperty.call(body, "sql_database_path")) {
    return normalizeStoredSqlDatabasePath(body.sql_database_path);
  }
  return normalizeStoredSqlDatabasePath(currentConfig?.sql_database_path);
}

async function handleSaveConfigRoute({ request, response, context }) {
  if (!requireAdminSession(context, request, response)) {
    return;
  }
  try {
    const body = await readJsonBody(request);
    await persistRuntimeApiKeys(context.appPaths.state_dir, { ...context.getRuntimeConfig(), ...body });
    const sanitizedBody = { ...body, llm_api_key: "", embedding_api_key: "" };
    const sanitizedCurrent = { ...context.getConfig(), llm_api_key: "", embedding_api_key: "" };
    const sqlDatabasePath = pickNextSqlDatabasePath(context.getConfig(), body);
    if (sqlDatabasePath) {
      assertSqlDatabaseAccessible(context.rootDir, {
        ...context.getConfig(),
        sql_database_path: sqlDatabasePath
      });
    }
    context.setConfigState(await saveConfigState(context.appPaths.config_dir, sanitizedBody, sanitizedCurrent));
    context.reloadAgent?.();
  } catch (error) {
    if (error instanceof FrontendPolicyValidationError) {
      json(response, 400, { error: error.message, field: "frontend_policy", status: error.status, policy_path: error.policy_path });
      return;
    }
    if (error instanceof SqlDatabasePathError) {
      json(response, 400, { error: error.message, field: error.field });
      return;
    }
    throw error;
  }
  if (context.getRuntimeConfig().admin_secret) {
    setAdminCookie(context.vaultDir, response, context.adminSessions.create(context.getRuntimeConfig().admin_secret), request);
  }
  json(response, 200, { status: "ok", config: await context.getProtectedConfig() });
}

async function handleTestLlmRoute({ request, response, context }) {
  const runtimeConfig = requireAdminSession(context, request, response);
  if (!runtimeConfig) {
    return;
  }
  const credentialState = await context.getCredentialState();
  if (credentialState.auth_mode === "oauth" && credentialState.oauth_session.status === "connected") {
    json(response, 409, { status: "error", message: "LLM test is disabled while an OAuth session is active." });
    return;
  }
  const body = await readJsonBody(request);
  const payload = buildLlmHealthPayload(body, context.getConfig(), runtimeConfig, defaultBaseUrl);
  payload.apiKey = payload.apiKey || await getTargetApiKey(context.appPaths.state_dir, "llm_shared", { ...runtimeConfig, llm_provider: payload.provider, llm_base_url: payload.baseUrl });
  json(response, 200, await runLlmHealthCheck(payload));
}

async function handleTestEmbeddingRoute({ request, response, context }) {
  const runtimeConfig = requireAdminSession(context, request, response);
  if (!runtimeConfig) {
    return;
  }
  const body = await readJsonBody(request);
  const payload = buildEmbeddingHealthPayload(body, context.getConfig(), runtimeConfig, defaultBaseUrl);
  payload.apiKey = payload.apiKey || await getTargetApiKey(context.appPaths.state_dir, "embeddings", { ...runtimeConfig, embedding_provider: payload.provider, embedding_base_url: payload.baseUrl });
  json(response, 200, await runEmbeddingHealthCheck(payload));
}

async function handleModelCatalogRoute({ request, response, context }) {
  const runtimeConfig = requireAdminSession(context, request, response);
  if (!runtimeConfig) {
    return;
  }
  json(
    response,
    200,
    await refreshModelCatalogGroup(
      context.appPaths.state_dir,
      runtimeConfig,
      context.getFrontendPolicy(),
      await buildResolvedModelCatalogPayload(request, context, runtimeConfig)
    )
  );
}

function normalizeCredentialTarget(value) {
  const normalized = String(value || "").trim();
  if (normalized === "embeddings" || normalized === "embedding") return "embeddings";
  if (normalized === "llm_shared" || normalized === "llm") return "llm_shared";
  return "";
}

function runtimeOverlayForCredentialTarget(runtimeConfig, target, body) {
  const provider = String(body.provider || "").trim();
  const baseUrl = String(body.base_url || body.baseUrl || "").trim();
  if (target === "embeddings") {
    return {
      ...runtimeConfig,
      embedding_provider: provider || runtimeConfig.embedding_provider,
      embedding_base_url: baseUrl || runtimeConfig.embedding_base_url
    };
  }
  return {
    ...runtimeConfig,
    llm_provider: provider || runtimeConfig.llm_provider,
    llm_base_url: baseUrl || runtimeConfig.llm_base_url
  };
}

async function handleDeleteApiKeyRoute({ request, response, context }) {
  const runtimeConfig = requireAdminSession(context, request, response);
  if (!runtimeConfig) {
    return;
  }
  const body = await readJsonBody(request);
  const target = normalizeCredentialTarget(body.group || body.target);
  if (!target) {
    json(response, 400, { error: "Credential target must be llm_shared or embeddings." });
    return;
  }
  const overlay = runtimeOverlayForCredentialTarget(runtimeConfig, target, body);
  const result = await deleteTargetApiKey(context.appPaths.state_dir, target, overlay);
  context.reloadAgent?.();
  const label = target === "embeddings" ? "Embedding provider" : "LLM provider";
  const message = result.deleted
    ? `${label} API key for ${result.provider_label} was deleted.`
    : `No ${label.toLowerCase()} API key was saved for ${result.provider_label}.`;
  json(response, 200, {
    status: "ok",
    deleted: result.deleted,
    group: target,
    provider: result.provider_settings.provider_id,
    base_url: result.provider_settings.base_url,
    message,
    config: await context.getProtectedConfig()
  });
}

async function buildResolvedModelCatalogPayload(request, context, runtimeConfig) {
  const body = await readJsonBody(request);
  const payload = buildModelCatalogPayload(body, context.getConfig(), runtimeConfig);
  if (!payload.apiKey) {
    const runtimeOverlay = payload.group === "embeddings"
      ? { ...runtimeConfig, embedding_provider: payload.provider, embedding_base_url: payload.baseUrl }
      : { ...runtimeConfig, llm_provider: payload.provider, llm_base_url: payload.baseUrl };
    payload.apiKey = await getTargetApiKey(
      context.appPaths.state_dir,
      payload.group === "embeddings" ? "embeddings" : "llm_shared",
      runtimeOverlay
    );
  }
  return payload;
}

export function createConfigRoutes({ exact }) {
  return [
    exact("config-current", "workflow", "GET", "/config/api/current", handleCurrentConfigRoute),
    exact("config-unlock", "workflow", "POST", "/config/api/unlock", handleUnlockConfigRoute),
    exact("config-save", "workflow", "POST", "/config/api/save", handleSaveConfigRoute),
    exact("config-delete-api-key", "workflow", "POST", "/config/api/delete-api-key", handleDeleteApiKeyRoute),
    exact("config-test-llm", "workflow", "POST", "/config/api/test-llm", handleTestLlmRoute),
    exact("config-test-embedding", "workflow", "POST", "/config/api/test-embedding", handleTestEmbeddingRoute),
    exact("config-models", "workflow", "POST", "/config/api/models", handleModelCatalogRoute)
  ];
}
