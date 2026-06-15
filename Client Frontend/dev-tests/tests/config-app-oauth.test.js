import assert from "node:assert/strict";
import test from "node:test";

import { createConfigApp } from "../../src/config_app.ts";
import { createApi, createConfig, createDom } from "./config-app-test-fixtures.js";

test("boot renders the OAuth card and disables the LLM test under an active session", async () => {
  const dom = createDom();
  const app = createConfigApp({
    api: createApi({
      getCurrentConfig: async () => createConfig({
        credential_state: {
          ...createConfig().credential_state,
          auth_mode: "oauth",
          oauth_session: {
            status: "connected",
            account_label: "OpenAI Account demo",
            status_message: "OpenAI OAuth is active.",
            client_id_hint: "app_...hann",
            scope: "openid profile",
            expires_at: "2099-01-01T00:00:00.000Z",
            account_id: "account-1",
            has_refresh_token: true
          }
        }
      })
    }),
    document: dom.window.document
  });

  await app.boot();

  assert.equal(dom.window.document.querySelector("#oauth-account").textContent, "OpenAI Account demo");
  assert.equal(dom.window.document.querySelector("#oauth-refresh").textContent, "Present");
  assert.equal(dom.window.document.querySelector("#llm-test").disabled, true);
});

test("logoutFromOAuth updates the current config and re-enables the LLM test", async () => {
  const dom = createDom();
  const app = createConfigApp({
    api: createApi({
      getCurrentConfig: async () => createConfig({
        credential_state: {
          ...createConfig().credential_state,
          auth_mode: "oauth",
          oauth_session: {
            status: "connected",
            account_label: "OpenAI Account demo",
            status_message: "OpenAI OAuth is active.",
            client_id_hint: "app_...hann",
            scope: "openid profile",
            expires_at: "2099-01-01T00:00:00.000Z",
            account_id: "account-1",
            has_refresh_token: true
          }
        }
      }),
      logoutOAuth: async () => ({ status: "ok", config: createConfig() })
    }),
    document: dom.window.document
  });

  await app.boot();
  await app.logoutFromOAuth();

  assert.equal(dom.window.document.querySelector("#oauth-mode").textContent, "API key fallback");
  assert.equal(dom.window.document.querySelector("#llm-test").disabled, false);
});

test("provider-specific key status does not present one saved key as global", async () => {
  const dom = createDom();
  const app = createConfigApp({
    api: createApi({
      getCurrentConfig: async () => createConfig({
        llm_provider: "openrouter",
        llm_base_url: "https://openrouter.ai/api/v1",
        credential_state: {
          ...createConfig().credential_state,
          oauth_supported: false,
          oauth_provider_label: "OpenRouter (https://openrouter.ai/api/v1)",
          targets: {
            ...createConfig().credential_state.targets,
            llm_shared: {
              has_secret: true,
              ready: true,
              source: "llm_api_key",
              fallback_available: true,
              message: "LLM provider API key for OpenRouter (https://openrouter.ai/api/v1) is saved."
            }
          }
        }
      })
    }),
    document: dom.window.document
  });

  await app.boot();

  assert.equal(
    dom.window.document.querySelector("#llm-api-key-current").textContent,
    "LLM provider API key for OpenRouter (https://openrouter.ai/api/v1) is saved."
  );

  const providerSelect = dom.window.document.querySelector("#llm-provider");
  providerSelect.value = "openai";
  providerSelect.dispatchEvent(new dom.window.Event("change", { bubbles: true }));

  assert.equal(
    dom.window.document.querySelector("#llm-api-key-current").textContent,
    "Save to check provider-specific key for OpenAI."
  );
  assert.equal(dom.window.document.querySelector("#oauth-mode").textContent, "Save required");
  assert.equal(
    dom.window.document.querySelector("#oauth-status").textContent,
    "Save OpenAI as the LLM provider before OAuth login."
  );
  assert.equal(dom.window.document.querySelector("#oauth-login").disabled, true);
});

test("typing a key after changing provider explains where it will be saved", async () => {
  const dom = createDom();
  const app = createConfigApp({
    api: createApi({
      getCurrentConfig: async () => createConfig({
        llm_provider: "openrouter",
        llm_base_url: "https://openrouter.ai/api/v1",
        credential_state: {
          ...createConfig().credential_state,
          oauth_supported: false,
          targets: {
            ...createConfig().credential_state.targets,
            llm_shared: {
              has_secret: true,
              ready: true,
              source: "llm_api_key",
              fallback_available: true,
              message: "LLM provider API key for OpenRouter (https://openrouter.ai/api/v1) is saved."
            }
          }
        }
      })
    }),
    document: dom.window.document
  });

  await app.boot();

  const providerSelect = dom.window.document.querySelector("#llm-provider");
  providerSelect.value = "openai";
  providerSelect.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  const apiKeyInput = dom.window.document.querySelector("#llm-api-key");
  apiKeyInput.value = "sk-openai";
  apiKeyInput.dispatchEvent(new dom.window.Event("input", { bubbles: true }));

  assert.equal(
    dom.window.document.querySelector("#llm-api-key-current").textContent,
    "New key will be saved for OpenAI."
  );
});

test("delete API key uses the selected provider slot without resetting unsaved provider selection", async () => {
  const dom = createDom();
  let deletePayload;
  const app = createConfigApp({
    api: createApi({
      getCurrentConfig: async () => createConfig(),
      deleteApiKey: async (payload) => {
        deletePayload = payload;
        return {
          status: "ok",
          deleted: true,
          group: "llm_shared",
          provider: "openrouter",
          base_url: "https://openrouter.ai/api/v1",
          message: "LLM provider API key for OpenRouter (https://openrouter.ai/api/v1) was deleted.",
          config: createConfig()
        };
      }
    }),
    document: dom.window.document
  });

  await app.boot();

  const providerSelect = dom.window.document.querySelector("#llm-provider");
  providerSelect.value = "openrouter";
  providerSelect.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  const baseUrlInput = dom.window.document.querySelector("#llm-base-url");
  baseUrlInput.value = "https://openrouter.ai/api/v1";
  baseUrlInput.dispatchEvent(new dom.window.Event("input", { bubbles: true }));

  dom.window.document.querySelector("#llm-key-delete").click();
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(deletePayload, {
    group: "llm_shared",
    provider: "openrouter",
    base_url: "https://openrouter.ai/api/v1"
  });
  assert.equal(providerSelect.value, "openrouter");
  assert.equal(
    dom.window.document.querySelector("#llm-api-key-current").textContent,
    "LLM provider API key for OpenRouter (https://openrouter.ai/api/v1) was deleted."
  );
});
