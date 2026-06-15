import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { createConfigApp } from "../../src/config_app.ts";
import { createApi, createConfig, createDom } from "./config-app-test-fixtures.js";

const CONFIG_DOMAIN_CSS = readFileSync(new URL("../../client_frontend/browser/styles/main/config_domain.css", import.meta.url), "utf8");

test("boot hydrates grouped frontend_policy editors and removes raw JSON UI", async () => {
  const dom = createDom();
  const app = createConfigApp({ api: createApi(), document: dom.window.document });

  await app.boot();

  assert.equal(dom.window.document.querySelector("#frontend-policy-input"), null);
  assert.equal(dom.window.document.querySelector("#fp-chat-max-history").value, "100");
  assert.match(dom.window.document.querySelector("#fp-memory-query-stop-words").value, /aber/);
  assert.equal(dom.window.document.querySelector("#fp-prompt-identity").value.length > 0, true);
  assert.equal(dom.window.document.querySelector("#fp-ontology-prompt-identity").value.length > 0, true);
  assert.equal(dom.window.document.querySelector('[data-config-panel="advanced"]').hidden, true);
  assert.equal(dom.window.document.querySelector('[data-config-panel="prompts"]').hidden, true);
});

test("config tabs expose prompt and advanced policy separately", async () => {
  const dom = createDom();
  const app = createConfigApp({ api: createApi(), document: dom.window.document });

  await app.boot();
  dom.window.document.querySelector('[data-config-tab="prompts"]').click();

  assert.equal(dom.window.document.querySelector('[data-config-panel="prompts"]').hidden, false);
  assert.equal(dom.window.document.querySelector('[data-config-panel="advanced"]').hidden, true);
  assert.equal(dom.window.document.querySelector('[data-policy-prompt-panel="query"]').hidden, false);
  assert.equal(dom.window.document.querySelector('[data-policy-prompt-panel="ontology"]').hidden, true);

  dom.window.document.querySelector('[data-policy-prompt-tab="ontology"]').click();
  assert.equal(dom.window.document.querySelector('[data-policy-prompt-panel="query"]').hidden, true);
  assert.equal(dom.window.document.querySelector('[data-policy-prompt-panel="ontology"]').hidden, false);

  dom.window.document.querySelector('[data-config-tab="advanced"]').click();
  assert.equal(dom.window.document.querySelector('[data-config-panel="prompts"]').hidden, true);
  assert.equal(dom.window.document.querySelector('[data-config-panel="advanced"]').hidden, false);
});

test("top-level config tabs stay outside the lockable form", () => {
  const dom = createDom();
  const tabs = Array.from(dom.window.document.querySelectorAll("[data-config-tab]"));

  assert.ok(tabs.length > 0);
  assert.equal(tabs.every((tab) => tab.closest("#config-form") === null), true);
});

test("config css does not override hidden tab panels", () => {
  assert.match(CONFIG_DOMAIN_CSS, /\.config-card\[hidden\]/);
  assert.match(CONFIG_DOMAIN_CSS, /display:\s*none/);
});

test("boot shows invalid stored diagnostics while keeping structured default values", async () => {
  const dom = createDom();
  const app = createConfigApp({
    api: createApi({
      getCurrentConfig: async () =>
        createConfig({
        frontend_policy_diagnostics: {
            status: "invalid_json",
            message: "frontend_policy.json is not valid JSON.",
            raw_text: "{ broken"
          }
        })
    }),
    document: dom.window.document
  });

  await app.boot();

  assert.equal(dom.window.document.querySelector("#fp-chat-max-history").value, "100");
  assert.match(dom.window.document.querySelector("#frontend-policy-status").textContent, /default values/i);
});

test("collectPayload normalizes multiline lists and regex rows", async () => {
  const dom = createDom();
  const app = createConfigApp({ api: createApi(), document: dom.window.document });

  await app.boot();
  dom.window.document.querySelector("#fp-memory-query-stop-words").value = "telekom\ntelekom\n rechnung \n";
  dom.window.document.querySelector("#fp-model-llm-seed-models").value = "gpt-4.1\n\ngpt-5\n";
  dom.window.document.querySelector("#fp-ontology-prompt-mission").value = "Custom ontology mission.";
  dom.window.document.querySelector('[data-add-regex="memory-filler-patterns"]').click();
  const rows = dom.window.document.querySelectorAll('[data-regex-rows="memory-filler-patterns"] [data-regex-row]');
  rows[rows.length - 1].querySelector('[data-regex-role="pattern"]').value = "^foo";
  rows[rows.length - 1].querySelector('[data-regex-role="flags"]').value = "i";

  const payload = app.collectPayload();

  assert.deepEqual(payload.frontend_policy.memory.query_stop_words, ["telekom", "rechnung"]);
  assert.deepEqual(payload.frontend_policy.model_catalog.llm_seed_models, ["gpt-4.1", "gpt-5"]);
  assert.equal(payload.frontend_policy.ontology_agent.prompt.mission, "Custom ontology mission.");
  assert.equal(payload.frontend_policy.memory.filler_patterns.at(-1).pattern, "^foo");
  assert.equal(payload.frontend_policy.memory.filler_patterns.at(-1).flags, "i");
});

test("submitSave rejects duplicate source order locally and highlights the field", async () => {
  const dom = createDom();
  let saveCalls = 0;
  const app = createConfigApp({
    api: createApi({
      saveConfig: async () => {
        saveCalls += 1;
        return { status: "ok", config: createConfig() };
      }
    }),
    document: dom.window.document
  });

  await app.boot();
  dom.window.document.querySelector("#fp-model-llm-source-order-0").value = "live";
  dom.window.document.querySelector("#fp-model-llm-source-order-1").value = "live";
  await app.submitSave();

  assert.equal(saveCalls, 0);
  assert.match(dom.window.document.querySelector("#frontend-policy-status").textContent, /llm_source_order/i);
  assert.equal(dom.window.document.activeElement.id, "fp-model-llm-source-order-0");
});

test("submitSave routes server frontend_policy validation errors to the matching grouped field", async () => {
  const dom = createDom();
  const app = createConfigApp({
    api: createApi({
      saveConfig: async () => {
        const error = new Error("frontend_policy.min_agent.runtime.max_tool_rounds muss eine Ganzzahl zwischen 1 und 256 sein.");
        error.payload = {
          field: "frontend_policy",
          error: error.message,
          policy_path: "frontend_policy.min_agent.runtime.max_tool_rounds"
        };
        throw error;
      }
    }),
    document: dom.window.document
  });

  await app.boot();
  await app.submitSave();

  assert.match(dom.window.document.querySelector("#frontend-policy-status").textContent, /max_tool_rounds/i);
  assert.equal(dom.window.document.activeElement.id, "fp-runtime-max-tool-rounds");
});

test("submitSave reports both config artifacts on success", async () => {
  const dom = createDom();
  const app = createConfigApp({ api: createApi(), document: dom.window.document });

  await app.boot();
  await app.submitSave();

  assert.match(dom.window.document.querySelector("#save-status").textContent, /config\.json and frontend_policy\.json saved/i);
});
