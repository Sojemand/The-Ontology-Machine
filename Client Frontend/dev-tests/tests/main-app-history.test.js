import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "../../src/api/client.ts";
import { createAppHarness, deferred, health, historyEntry, source } from "./main-app-fixtures.js";

test("two quick restore requests keep the latest chat response", async () => {
  const { app, api } = createAppHarness();
  await app.boot();

  const first = deferred();
  const second = deferred();
  api.restoreChat = async (chatId) => (chatId === "chat-a" ? first.promise : second.promise);

  const firstRestore = app.restoreHistoryEntry("chat-a");
  const secondRestore = app.restoreHistoryEntry("chat-b");

  second.resolve({
    title: "Chat B",
    messages: [
      { role: "user", content: "Question B" },
      { role: "assistant", content: "Answer B", sources: [source({ id: "doc-b", file_name: "b.pdf" })] }
    ]
  });
  await secondRestore;

  first.resolve({
    title: "Chat A",
    messages: [
      { role: "user", content: "Question A" },
      { role: "assistant", content: "Answer A", sources: [source({ id: "doc-a", file_name: "a.pdf" })] }
    ]
  });
  await firstRestore;

  assert.deepEqual(app.getState().messages.map((message) => message.content), [
    "Welcome. Ask a question about your document archive. Answers are generated only from the local corpus.",
    "Question B",
    "Answer B"
  ]);
});

test("double new chat calls do not create stale UI state", async () => {
  const { app, api } = createAppHarness({
    restoreChat: async () => ({
      title: "Vorher",
      messages: [
        { role: "user", content: "Previous question" },
        { role: "assistant", content: "Previous answer", sources: [source()] }
      ]
    })
  });
  await app.boot();
  await app.restoreHistoryEntry("existing");

  const gate = deferred();
  let callCount = 0;
  api.newChat = async () => ((callCount += 1), gate.promise);

  const firstNewChat = app.startNewChat();
  const secondNewChat = app.startNewChat();

  gate.resolve({ status: "ok" });
  await Promise.all([firstNewChat, secondNewChat]);

  assert.equal(callCount, 1);
  assert.deepEqual(app.getState().messages.map((message) => message.content), [
    "Welcome. Ask a question about your document archive. Answers are generated only from the local corpus."
  ]);
});

test("parallel history refreshes keep the latest list", async () => {
  const { app, api, dom } = createAppHarness();
  await app.boot();

  const first = deferred();
  const second = deferred();
  let callCount = 0;
  api.getChatHistory = async () => ((callCount += 1), callCount === 1 ? first.promise : second.promise);

  const firstRefresh = app.refreshHistoryList();
  const secondRefresh = app.refreshHistoryList();

  second.resolve({ chats: [historyEntry("chat-b", "Neu")] });
  await secondRefresh;

  first.resolve({ chats: [historyEntry("chat-a", "Alt")] });
  await firstRefresh;

  const historyList = dom.window.document.querySelector("#history-list");
  assert.match(historyList.textContent || "", /Neu/);
  assert.doesNotMatch(historyList.textContent || "", /Alt/);
});

test("switching to pipeline keeps a separate view and shows the root-folder abort", async () => {
  const historyAgents = [];
  const { app, dom } = createAppHarness({
    getChatHistory: async (agent = "query") => {
      historyAgents.push(agent);
      return { chats: [historyEntry(`${agent}-chat`, `${agent} history`)] };
    }
  });
  await app.boot();

  await app.switchAgent("pipeline");

  assert.equal(app.getState().activeAgentType, "pipeline");
  assert.deepEqual(app.getState().messages.map((message) => message.content), [
    "Taxonomy Agent ready."
  ]);
  assert.equal(dom.window.document.querySelector("#pipeline-permission-status")?.textContent, "Choose Pipeline Root Folder");
  assert.equal(dom.window.document.querySelector('[data-agent="pipeline"]')?.getAttribute("aria-pressed"), "true");
  assert.ok(historyAgents.includes("pipeline"));
});

test("switching to ontology keeps a separate view and routes history to ontology", async () => {
  const historyAgents = [];
  const { app, dom } = createAppHarness({
    getChatHistory: async (agent = "query") => {
      historyAgents.push(agent);
      return { chats: [historyEntry(`${agent}-chat`, `${agent} history`)] };
    }
  });
  await app.boot();

  await app.switchAgent("ontology");

  assert.equal(app.getState().activeAgentType, "ontology");
  assert.deepEqual(app.getState().messages.map((message) => message.content), [
    "Ontology Agent ready."
  ]);
  assert.equal(dom.window.document.querySelector('[data-agent="ontology"]')?.getAttribute("aria-pressed"), "true");
  assert.ok(historyAgents.includes("ontology"));
});

test("pipeline startup status is refreshed when the manager becomes ready", async () => {
  let healthCalls = 0;
  const startupManager = {
    available: false,
    reason: "Taxonomy Agent is still starting.",
    startup_pending: true,
    permission_status: null,
    permission_warning: ""
  };
  const readyManager = {
    available: true,
    reason: "",
    tool_count: 30,
    semantic_control_kernel_tool_count: 30,
    pending_kernel_event_count: 0,
    permission_status: null,
    permission_warning: ""
  };
  const { app, dom } = createAppHarness({
    getHealth: async () => health({
      pipeline_manager: (healthCalls += 1) === 1 ? startupManager : readyManager
    })
  });

  await app.boot();
  await app.switchAgent("pipeline");

  assert.match(dom.window.document.querySelector("#chat-status")?.textContent || "", /Taxonomy Agent is still starting/);

  await app.refreshRuntimeStatus();

  assert.equal(dom.window.document.querySelector("#chat-status")?.textContent, "Ready.");
  assert.match(dom.window.document.querySelector("#pipeline-permission-status")?.textContent || "", /Kernel tools ready: 30/);
});

test("pipeline chat config errors show the server message instead of fetch failed", async () => {
  const { app, dom } = createAppHarness({
    getHealth: async () => health({
      pipeline_manager: {
        available: true,
        reason: "",
        tool_count: 30,
        semantic_control_kernel_tool_count: 30,
        permission_status: null,
        permission_warning: ""
      }
    }),
    sendChat: async () => {
      throw new ApiError("Choose Pipeline Root Folder", 409, { field: "pipeline_root" });
    },
    getPipelineKernelEvents: async () => ({ schema_version: "kernel.client_frontend_event_batch.v1", cursor: "", events: [] })
  });
  await app.boot();
  await app.switchAgent("pipeline");

  const input = dom.window.document.querySelector("#chat-input");
  const form = dom.window.document.querySelector("#chat-form");
  input.value = "kernel_status";
  form.dispatchEvent(new dom.window.Event("submit", { bubbles: true, cancelable: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(dom.window.document.querySelector("#chat-status")?.textContent, "Choose Pipeline Root Folder");
  assert.match(dom.window.document.querySelector("#messages")?.textContent || "", /Could not generate an answer.: Choose Pipeline Root Folder/);
});
