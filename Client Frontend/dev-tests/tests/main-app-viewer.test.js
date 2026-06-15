import assert from "node:assert/strict";
import test from "node:test";

import { createAppHarness, source } from "./main-app-fixtures.js";

test("viewer ignores stale image events from replaced image nodes", async () => {
  const { app, dom } = createAppHarness();
  await app.boot();

  app.selectSource(source({ id: "doc-1", file_name: "one.pdf" }));
  const firstImage = dom.window.document.querySelector("#viewer-image");

  app.selectSource(source({ id: "doc-2", file_name: "two.pdf" }));
  const secondImage = dom.window.document.querySelector("#viewer-image");

  assert.notEqual(firstImage, secondImage);

  firstImage.dispatchEvent(new dom.window.Event("error"));
  assert.equal(app.getState().viewer.imageFailed, false);
  assert.equal(dom.window.document.querySelector("#viewer-placeholder").hidden, true);

  secondImage.dispatchEvent(new dom.window.Event("error"));
  assert.equal(app.getState().viewer.imageFailed, true);
  assert.equal(dom.window.document.querySelector("#viewer-placeholder").hidden, false);

  app.selectSource(source({ id: "doc-3", file_name: "three.pdf" }));
  const thirdImage = dom.window.document.querySelector("#viewer-image");
  secondImage.dispatchEvent(new dom.window.Event("load"));
  thirdImage.dispatchEvent(new dom.window.Event("load"));

  assert.equal(app.getState().viewer.imageFailed, false);
  assert.equal(dom.window.document.querySelector("#viewer-placeholder").hidden, true);
});

test("viewer page and zoom controls follow the staged workflow", async () => {
  const { app, dom } = createAppHarness();
  await app.boot();

  app.selectSource(source({ id: "doc-9", page_count: 3, viewer_available: true }));
  dom.window.document.querySelector("#page-next").click();
  dom.window.document.querySelector("#zoom-in").click();

  const viewerStage = dom.window.document.querySelector("#viewer-stage");
  viewerStage.dispatchEvent(new dom.window.WheelEvent("wheel", { deltaY: -120, clientX: 180, clientY: 120, bubbles: true, cancelable: true }));

  const zoomedState = app.getState();
  assert.equal(zoomedState.viewer.page, 2);
  assert.ok(zoomedState.viewer.zoom > 1.2);

  dom.window.document.querySelector("#zoom-reset").click();
  const resetState = app.getState();
  assert.equal(resetState.viewer.zoom, 1);
  assert.equal(resetState.viewer.offsetX, 0);
  assert.equal(resetState.viewer.offsetY, 0);
});
