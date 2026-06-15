import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

const CONFIG_HTML = readFileSync(new URL("../../src/config.html", import.meta.url), "utf8");

export function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

export function createDom() {
  return new JSDOM(CONFIG_HTML, { url: "http://127.0.0.1:3001/config" });
}

export function createConfig(overrides = {}) {
  return {
    customer_name: "Vision Pipeline Case Worker",
    sql_database_path: "",
    pipeline_root: "",
    llm_provider: "openai",
    llm_base_url: "https://api.openai.com/v1",
    llm_model: "gpt-5.4",
    llm_api_key: "",
    embedding_provider: "openai",
    embedding_base_url: "https://api.openai.com/v1",
    embedding_model: "text-embedding-3-small",
    embedding_api_key: "",
    port: 3000,
    theme: "dark",
    admin_secret: "",
    protected: false,
    context_limit: 127096,
    frontend_policy: buildDefaultFrontendPolicy(),
    credential_state: {
      auth_mode: "api_keys",
      oauth_session: {
        status: "logged_out",
        account_label: "",
        status_message: "No active OAuth login.",
        client_id_hint: "",
        scope: "",
        expires_at: "",
        account_id: "",
        has_refresh_token: false
      },
      targets: {
        llm_shared: {
          has_secret: false,
          ready: false,
          source: "",
          fallback_available: false,
          message: "No LLM API key saved."
        },
        embeddings: {
          has_secret: false,
          ready: false,
          source: "",
          fallback_available: false,
          message: "No embedding key saved."
        }
      },
      model_catalog: {
        llm_shared: {
          models: [
            "gpt-5.5-pro",
            "gpt-5.5",
            "gpt-5.5-mini",
            "gpt-5.5-nano",
            "gpt-5.4-pro",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.2-pro",
            "gpt-5.2",
            "gpt-5.2-mini",
            "gpt-5.2-nano",
            "gpt-5.1",
            "gpt-5.1-mini",
            "gpt-5.1-nano",
            "gpt-5-pro",
            "gpt-5",
            "gpt-5-chat-latest",
            "gpt-5-mini",
            "gpt-5-nano"
          ],
          refreshed_at: "",
          source: "seed"
        },
        embeddings: {
          models: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
          refreshed_at: "",
          source: "seed"
        }
      }
    },
    ...overrides
  };
}

export function createModelsResponse(overrides = {}) {
  return {
    llm_models: ["gpt-4.1", "gpt-4o-mini"],
    embedding_models: ["text-embedding-3-small", "text-embedding-3-large"],
    context_limits: {
      "gpt-4.1": 128000,
      "gpt-4o-mini": 128000
    },
    source: "live",
    updated_at: "2026-03-24T12:00:00.000Z",
    ...overrides
  };
}

export function createApi(overrides = {}) {
  return {
    getCurrentConfig: async () => createConfig(),
    getModels: async () => createModelsResponse(),
    deleteApiKey: async (payload) => ({ status: "ok", deleted: true, message: "Deleted.", config: createConfig(), ...payload }),
    logoutOAuth: async () => ({ status: "ok", config: createConfig() }),
    saveConfig: async (payload) => ({ status: "ok", config: createConfig(payload) }),
    testEmbedding: async () => ({ status: "ok", message: "Embedding OK" }),
    testLlm: async () => ({ status: "ok", message: "LLM OK" }),
    unlockConfig: async () => ({ status: "ok" }),
    ...overrides
  };
}

export function optionValues(select) {
  return Array.from(select.options).map((option) => option.value);
}
