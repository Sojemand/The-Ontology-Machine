import assert from "node:assert/strict";
import test from "node:test";

import { clampLayoutState, createTokenCounterPresentation, createTurnCounterPresentation } from "../../src/main_app/policy.ts";
import { createMainApp } from "../../src/main_app.ts";
import { createApi, createDom } from "./main-app-fixtures.js";

test("invalid stored layout values are clamped back to valid state", async () => {
  const dom = createDom();
  dom.window.localStorage.setItem("vp-layout-sidebar-width", "999999");
  dom.window.localStorage.setItem("vp-layout-viewer-width", "-20");
  dom.window.localStorage.setItem("vp-layout-secondary-width", "-500");
  dom.window.localStorage.setItem("vp-layout-active-pane", "invalid-pane");

  const app = createMainApp({ api: createApi(), document: dom.window.document, window: dom.window });
  await app.boot();

  const state = app.getState();
  assert.equal(state.layout.activePane, "chat");
  assert.ok(state.layout.sidebarWidth >= 220 && state.layout.sidebarWidth <= 460);
  assert.ok(state.layout.viewerWidth >= 240 && state.layout.viewerWidth <= 520);
  assert.ok(state.layout.secondaryWidth >= 240 && state.layout.secondaryWidth <= 460);
});

test("user theme selection is persisted and survives health refreshes", async () => {
  const dom = createDom();
  const app = createMainApp({ api: createApi(), document: dom.window.document, window: dom.window });
  await app.boot();

  assert.ok(dom.window.document.body.classList.contains("theme-dark"));
  dom.window.document.querySelector("#theme-toggle").click();

  assert.equal(dom.window.localStorage.getItem("vp-main-theme"), "light");
  assert.ok(dom.window.document.body.classList.contains("theme-light"));

  await app.refreshRuntimeStatus();

  assert.equal(app.getState().theme, "light");
  assert.ok(dom.window.document.body.classList.contains("theme-light"));
  assert.ok(!dom.window.document.body.classList.contains("theme-dark"));
});

test("layout policy clamps widths and turn counter thresholds explicitly", () => {
  const clamped = clampLayoutState(
    { mode: "wide", density: "comfortable", activePane: "chat", sidebarWidth: 9999, viewerWidth: -10, secondaryWidth: -50 },
    980
  );
  const warning = createTurnCounterPresentation(9, 10);
  const over = createTurnCounterPresentation(10, 10);

  assert.ok(clamped.sidebarWidth >= 220 && clamped.sidebarWidth <= 460);
  assert.ok(clamped.viewerWidth >= 240 && clamped.viewerWidth <= 520);
  assert.equal(warning.state, "warning");
  assert.equal(over.state, "over");
});

test("token counter presentation formats estimated input and output totals", () => {
  const normal = createTokenCounterPresentation(578167, 7486);
  const over = createTokenCounterPresentation(1_100_000, 25_000);

  assert.equal(normal.text, "~In 578k | ~Out 7.5k");
  assert.equal(normal.state, "warning");
  assert.match(normal.title, /Input: ~578,167/);
  assert.match(normal.title, /Output: ~7,486/);
  assert.equal(over.state, "over");
});
