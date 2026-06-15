import assert from "node:assert/strict";
import test from "node:test";

import { createConfigApp } from "../../src/config_app.ts";
import { createApi, createConfig, createDom, deferred } from "./config-app-test-fixtures.js";

test("stale LLM test responses no longer overwrite the latest status", async () => {
  const dom = createDom();
  const api = createApi();
  const app = createConfigApp({ api, document: dom.window.document });
  const first = deferred();
  const second = deferred();
  let callCount = 0;

  await app.boot();

  api.testLlm = async () => {
    callCount += 1;
    return callCount === 1 ? first.promise : second.promise;
  };

  const firstTest = app.runLlmTest();
  const secondTest = app.runLlmTest();
  second.resolve({ status: "ok", message: "Neue Verbindung OK" });
  await secondTest;
  first.reject(new Error("Alte Fehlermeldung"));
  await firstTest;

  assert.equal(dom.window.document.querySelector("#llm-status").textContent, "Neue Verbindung OK");
});

test("unlock keeps the latest successful attempt when earlier failures resolve later", async () => {
  const dom = createDom();
  const api = createApi({
    getCurrentConfig: async () => createConfig({ protected: true, admin_secret: "configured" })
  });
  const app = createConfigApp({ api, document: dom.window.document });
  const first = deferred();
  const second = deferred();
  let callCount = 0;

  await app.boot();

  api.unlockConfig = async () => {
    callCount += 1;
    return callCount === 1 ? first.promise : second.promise;
  };

  const firstUnlock = app.submitUnlock("wrong");
  const secondUnlock = app.submitUnlock("right");
  second.resolve({ status: "ok" });
  await secondUnlock;
  first.reject(new Error("Falsches Admin-Passwort."));
  await firstUnlock;

  assert.equal(app.getState().unlocked, true);
  assert.equal(dom.window.document.querySelector("#unlock-status").textContent, "");
});

test("save keeps the latest response when older saves finish afterwards", async () => {
  const dom = createDom();
  const api = createApi();
  const app = createConfigApp({ api, document: dom.window.document });
  const first = deferred();
  const second = deferred();
  let callCount = 0;

  await app.boot();

  api.saveConfig = async () => {
    callCount += 1;
    return callCount === 1 ? first.promise : second.promise;
  };

  const customerNameInput = dom.window.document.querySelector("#customer-name-input");
  customerNameInput.value = "Erster Name";
  const firstSave = app.submitSave();
  customerNameInput.value = "Zweiter Name";
  const secondSave = app.submitSave();

  second.resolve({ status: "ok", config: createConfig({ customer_name: "Zweiter Name" }) });
  await secondSave;
  first.resolve({ status: "ok", config: createConfig({ customer_name: "Erster Name" }) });
  await firstSave;

  assert.equal(dom.window.document.querySelector("#config-title").textContent, "Zweiter Name");
  assert.equal(customerNameInput.value, "Zweiter Name");
  assert.equal(dom.window.document.querySelector("#save-config").disabled, false);
});
