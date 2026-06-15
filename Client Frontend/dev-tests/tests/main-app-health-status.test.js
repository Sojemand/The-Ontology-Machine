import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, health } from "./main-app-fixtures.js";

test("main health renders base graph and ontology lens status beside LLM readiness", async () => {
  const { app, dom } = createAppHarness({
    getHealth: async () => health({
      database_status: {
        base_graph: { available: true, source_document_count: 4, source_page_count: 9 },
        ontology_lenses: { available: true, count: 3, active_count: 1, primary_ontology_id: "lens_story" }
      }
    })
  });

  await app.boot();

  const baseGraph = dom.window.document.querySelector("#base-graph-pill");
  const lensCount = dom.window.document.querySelector("#ontology-lenses-count");

  assert.equal(baseGraph?.dataset.state, "ok");
  assert.equal(baseGraph?.textContent, "Base Graph ready");
  assert.equal(lensCount?.textContent, "3");
});

test("main health marks a stale base graph as dirty", async () => {
  const { app, dom } = createAppHarness({
    getHealth: async () => health({
      database_status: {
        base_graph: {
          available: true,
          dirty: true,
          source_document_count: 4,
          source_page_count: 9,
          unmapped_document_count: 2
        },
        ontology_lenses: { available: true, count: 1, active_count: 1, primary_ontology_id: "lens_story" }
      }
    })
  });

  await app.boot();

  const baseGraph = dom.window.document.querySelector("#base-graph-pill");

  assert.equal(baseGraph?.dataset.state, "warning");
  assert.equal(baseGraph?.textContent, "Base Graph dirty");
  assert.match(baseGraph?.getAttribute("title") || "", /2 document\(s\)/);
});

test("main health marks missing base graph red and keeps ontology lens count visible", async () => {
  const { app, dom } = createAppHarness({
    getHealth: async () => health({
      database_status: {
        base_graph: { available: false, source_document_count: 0, source_page_count: 0 },
        ontology_lenses: { available: true, count: 0, active_count: 0, primary_ontology_id: null }
      }
    })
  });

  await app.boot();

  const baseGraph = dom.window.document.querySelector("#base-graph-pill");
  const lensCount = dom.window.document.querySelector("#ontology-lenses-count");

  assert.equal(baseGraph?.dataset.state, "error");
  assert.equal(baseGraph?.textContent, "Base Graph missing");
  assert.equal(lensCount?.textContent, "0");
});

test("main chat renders cumulative estimated token usage beside the turn counter", async () => {
  const { app, dom } = createAppHarness({
    sendChat: async () => ({
      answer: "OK",
      sources: [],
      token_usage: { estimated: true, input_tokens: 578167, output_tokens: 7486, llm_calls: 6 }
    })
  });

  await app.boot();
  const input = dom.window.document.querySelector("#chat-input");
  input.value = "Token check";
  dom.window.document.querySelector("#chat-form").requestSubmit();
  await new Promise((resolve) => dom.window.setTimeout(resolve, 0));

  const counter = dom.window.document.querySelector("#token-counter");
  assert.equal(counter?.textContent, "~In 578k | ~Out 7.5k");
  assert.equal(counter?.dataset.state, "warning");
  assert.match(counter?.getAttribute("title") || "", /Input: ~578,167/);
});
