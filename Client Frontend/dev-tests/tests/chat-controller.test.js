import assert from "node:assert/strict";
import test from "node:test";

import { createChatController } from "../../src/chat_controller.ts";

test("controller accepts only the active send response", () => {
  const controller = createChatController();
  const request = controller.beginSend();

  assert.equal(controller.isSending(), true);
  assert.equal(controller.canApplyResponse(request), true);

  controller.finishSend(request);
  assert.equal(controller.isSending(), false);
});

test("stale response is rejected after new conversation reset", () => {
  const controller = createChatController();
  const request = controller.beginSend();

  controller.resetConversation();

  assert.equal(controller.canApplyResponse(request), false);
  controller.finishSend(request);
  assert.equal(controller.isSending(), false);
});

test("new send token supersedes the previous one", () => {
  const controller = createChatController();
  const first = controller.beginSend();
  const second = controller.beginSend();

  assert.equal(controller.canApplyResponse(first), false);
  assert.equal(controller.canApplyResponse(second), true);
});

test("finishing a stale request does not clear the active send", () => {
  const controller = createChatController();
  const first = controller.beginSend();
  const second = controller.beginSend();

  controller.finishSend(first);
  assert.equal(controller.isSending(), true);
  assert.equal(controller.canApplyResponse(second), true);

  controller.finishSend(second);
  assert.equal(controller.isSending(), false);
});

test("reset invalidates prior request tokens until a new send begins", () => {
  const controller = createChatController();
  const first = controller.beginSend();

  controller.resetConversation();
  const next = controller.beginSend();

  assert.equal(controller.canApplyResponse(first), false);
  assert.equal(controller.canApplyResponse(next), true);
});

