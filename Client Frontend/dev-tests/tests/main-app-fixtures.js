import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

import { createMainApp } from "../../src/main_app.ts";

const INDEX_HTML = readFileSync(new URL("../../src/index.html", import.meta.url), "utf8");

export function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

export function source(overrides = {}) {
  return {
    id: "doc-1",
    title: "Titel",
    type: "invoice",
    date: "2026-03-24",
    actor: "ACME",
    page: 1,
    page_count: 2,
    source_refs: [],
    snippet: "Snippet",
    image_url: "/api/image/doc-1/1",
    viewer_available: true,
    file_name: "alpha.pdf",
    ...overrides
  };
}

export function health(overrides = {}) {
  return {
    status: "ok",
    corpus_docs: 3,
    llm_model: "gpt-4.1",
    customer_name: "Test Customer",
    agent_name: "Test Agent",
    theme: "dark",
    llm_ready: true,
    embedding_ready: true,
    llm_auth_mode: "api_keys",
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
    pipeline_manager: {
      available: false,
      reason: "Choose Pipeline Root Folder",
      permission_status: null,
      permission_warning: ""
    },
    database_status: {
      base_graph: {
        available: true,
        source_document_count: 2,
        source_page_count: 3,
        structural_unit_count: 5,
        base_unit_count: 2,
        page_unit_count: 3,
        relation_count: 3
      },
      ontology_lenses: {
        available: true,
        count: 2,
        active_count: 1,
        primary_ontology_id: "lens_primary"
      }
    },
    context_limit: 127096,
    memory_turns: 12,
    ...overrides
  };
}

export function historyEntry(id, title) {
  return { id, title, created_at: 1710000000000, updated_at: 1710000000000, message_count: 2 };
}

export function createDom() {
  const dom = new JSDOM(INDEX_HTML, { url: "http://127.0.0.1:3000/" });
  Object.defineProperty(dom.window, "innerWidth", { configurable: true, value: 1600, writable: true });
  Object.defineProperty(dom.window, "innerHeight", { configurable: true, value: 1000, writable: true });
  if (!dom.window.HTMLFormElement.prototype.requestSubmit) {
    dom.window.HTMLFormElement.prototype.requestSubmit = function requestSubmit() {
      this.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
    };
  }
  if (!dom.window.Element.prototype.setPointerCapture) dom.window.Element.prototype.setPointerCapture = () => {};
  return dom;
}

export function createApi(overrides = {}) {
  return {
    getChatHistory: async () => ({ chats: [] }),
    getHealth: async () => health(),
    newChat: async () => ({ status: "ok" }),
    restoreChat: async () => ({ messages: [], title: "Leer" }),
    sendChat: async () => ({ answer: "OK", sources: [] }),
    cancelPipelineRun: async () => ({ status: "cancelled", run_cancelled: true }),
    resetKernelRuntimeState: async () => ({
      status: "ok",
      reset_id: "rst-test",
      created_at: "2026-05-09T10:00:00Z",
      archived_path_count: 0,
      preserved_paths: [],
      reason: "test",
      message: "Kernel runtime state was reset."
    }),
    getPipelineKernelEvents: async () => ({ schema_version: "kernel.client_frontend_event_batch.v1", cursor: "", events: [] }),
    submitKernelInteractionResponse: async () => ({
      bridge_response: {
        schema_version: "semantic_control_kernel.host_bridge_response.v1",
        status: "accepted",
        user_visible_summary: "Interaction accepted."
      },
      event_batch: { schema_version: "kernel.client_frontend_event_batch.v1", cursor: "", events: [] }
    }),
    cancelKernelInteraction: async () => ({
      bridge_response: {
        schema_version: "semantic_control_kernel.host_bridge_response.v1",
        status: "cancelled",
        user_visible_summary: "Interaction cancelled."
      },
      event_batch: { schema_version: "kernel.client_frontend_event_batch.v1", cursor: "", events: [] }
    }),
    ...overrides
  };
}

export function createAppHarness(overrides = {}) {
  const dom = createDom();
  const api = createApi(overrides);
  const app = createMainApp({ api, document: dom.window.document, window: dom.window });
  return { dom, api, app };
}
