import assert from "node:assert/strict";
import test from "node:test";

import { defaultBaseUrl, runLlmHealthCheck } from "../../server/provider.js";
import { jsonResponse, mockFetch } from "./provider-test-fixtures.js";

test("runLlmHealthCheck throws when choices array is empty", async () => {
  const restore = mockFetch(() => jsonResponse(200, { choices: [] }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "gpt-4.1" }),
      /No model response/
    );
  } finally {
    restore();
  }
});

test("runLlmHealthCheck throws when choices is missing entirely", async () => {
  const restore = mockFetch(() => jsonResponse(200, { id: "chatcmpl-123" }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "gpt-4.1" }),
      /No model response/
    );
  } finally {
    restore();
  }
});

test("runLlmHealthCheck throws on HTTP 429 rate limit", async () => {
  const restore = mockFetch(() => jsonResponse(429, { error: { message: "Rate limit exceeded" } }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "gpt-4.1" }),
      /Rate limit/
    );
  } finally {
    restore();
  }
});

test("runLlmHealthCheck propagates statusText when no error message in body", async () => {
  const restore = mockFetch(() => new Response("{}", { status: 503, statusText: "Service Unavailable" }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "gpt-4.1" }),
      /Service Unavailable/
    );
  } finally {
    restore();
  }
});

test("defaultBaseUrl with null/undefined returns OpenAI URL", () => {
  assert.equal(defaultBaseUrl(null), "https://api.openai.com/v1");
  assert.equal(defaultBaseUrl(undefined), "https://api.openai.com/v1");
  assert.equal(defaultBaseUrl(0), "https://api.openai.com/v1");
});

test("requestJson handles response with error.message field", async () => {
  const restore = mockFetch(() => jsonResponse(400, { error: { message: "Bad request: invalid model" } }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "bad" }),
      /Bad request: invalid model/
    );
  } finally {
    restore();
  }
});

test("requestJson handles response with message field (non-nested)", async () => {
  const restore = mockFetch(() => jsonResponse(400, { message: "Top-level error message" }));
  try {
    await assert.rejects(
      () => runLlmHealthCheck({ baseUrl: "https://api.openai.com/v1", apiKey: "sk-test", model: "bad" }),
      /Top-level error message/
    );
  } finally {
    restore();
  }
});
