import assert from "node:assert/strict";
import test from "node:test";

import { createConfigApp } from "../../src/config_app.ts";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";
import { createApi, createDom } from "./config-app-test-fixtures.js";

test("setSaveStatus stays available on the public surface", () => {
  const dom = createDom();
  const app = createConfigApp({ api: createApi(), document: dom.window.document });

  app.setSaveStatus("Manueller Fehler", "error");

  assert.equal(dom.window.document.querySelector("#save-status").textContent, "Manueller Fehler");
});

test("collectPayload exposes the named config contract from the DOM surface", async () => {
  const dom = createDom();
  const app = createConfigApp({ api: createApi(), document: dom.window.document });

  await app.boot();

  dom.window.document.querySelector("#customer-name-input").value = "ACME";
  dom.window.document.querySelector("#sql-database-path-input").value = "C:\\Data\\custom\\corpus.db";
  dom.window.document.querySelector("#pipeline-root-input").value = "C:\\Pipeline";
  dom.window.document.querySelector("#port-input").value = "4100";
  dom.window.document.querySelector("#theme-input").value = "light";
  dom.window.document.querySelector('input[name="llm_provider"][value="mammouth"]').checked = true;
  dom.window.document.querySelector("#llm-base-url").value = "https://mammouth.example/v1";
  dom.window.document.querySelector("#llm-model").value = "gpt-4o-mini";
  dom.window.document.querySelector("#llm-api-key").value = "llm-secret";
  dom.window.document.querySelector('input[name="embedding_provider"][value="mammouth"]').checked = true;
  dom.window.document.querySelector("#embedding-base-url").value = "https://embed.example/v1";
  dom.window.document.querySelector("#embedding-model").value = "text-embedding-3-large";
  dom.window.document.querySelector("#embedding-api-key").value = "embed-secret";
  dom.window.document.querySelector("#admin-secret-input").value = "admin-secret";
  dom.window.document.querySelector("#context-limit").value = "64000";

  assert.deepEqual(app.collectPayload(), {
    customer_name: "ACME",
    sql_database_path: "C:\\Data\\custom\\corpus.db",
    pipeline_root: "C:\\Pipeline",
    port: 4100,
    theme: "light",
    llm_provider: "mammouth",
    llm_base_url: "https://mammouth.example/v1",
    llm_model: "gpt-4o-mini",
    llm_api_key: "llm-secret",
    embedding_provider: "mammouth",
    embedding_base_url: "https://embed.example/v1",
    embedding_model: "text-embedding-3-large",
    embedding_api_key: "embed-secret",
    admin_secret: "admin-secret",
    context_limit: 64000,
    frontend_policy: buildDefaultFrontendPolicy()
  });
});
