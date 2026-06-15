import assert from "node:assert/strict";
import { rmSync } from "node:fs";
import test from "node:test";

import { saveToken } from "../../client_frontend/credentials/oauth_token_store.js";
import { createChatCompletion } from "../../server/provider.js";

import { createStateDir, healthyToken, jsonResponse, mockFetch } from "./provider-surface-support.js";

test("createChatCompletion prefers the OAuth backend when a healthy session is present", async () => {
  const stateDir = createStateDir();
  const calls = [];
  await saveToken(stateDir, healthyToken());
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    return new Response(
      'event: response.output_text.done\ndata: {"text":"oauth ok"}\n\nevent: response.completed\ndata: {"response":{"output":[{"type":"message","content":[{"type":"output_text","text":"oauth ok"}]}]}}\n\n', { status: 200, headers: { "Content-Type": "text/event-stream" } }
    );
  });
  try {
    const result = await createChatCompletion({
      state_dir: stateDir,
      llm_base_url: "https://api.openai.com/v1",
      llm_api_key: "sk-fallback",
      llm_model: "gpt-4.1"
    }, [
      { role: "user", content: "Hallo" },
      { role: "assistant", content: "Bereit." },
      { role: "user", content: "Bitte pruefen." }
    ], [{ type: "function", function: { name: "sql_query", parameters: {} } }]);

    assert.equal(calls.at(0).url, "https://chatgpt.com/backend-api/codex/responses");
    assert.equal(calls.at(0).init.headers.Authorization, "Bearer oauth-token");
    assert.equal(calls.at(0).init.headers["ChatGPT-Account-Id"], "account-1");
    const body = JSON.parse(calls.at(0).init.body);
    assert.equal(body.input[1].role, "assistant");
    assert.equal(body.input[1].content[0].type, "output_text");
    assert.equal(body.max_output_tokens, undefined);
    assert.equal(body.max_completion_tokens, undefined);
    assert.deepEqual(body.tools, [{ type: "function", name: "sql_query", description: "", parameters: {} }]);
    assert.equal(body.tools[0].function, undefined);
    assert.equal(result.choices[0].message.content, "oauth ok");
  } finally {
    restore();
    rmSync(stateDir, { recursive: true, force: true });
  }
});

test("createChatCompletion preserves OAuth streamed function calls when completed output is empty", async () => {
  const stateDir = createStateDir();
  await saveToken(stateDir, healthyToken());
  const restore = mockFetch(() => new Response([
    'event: response.output_item.added\ndata: {"item":{"id":"fc_123","type":"function_call","status":"in_progress","arguments":"","call_id":"call_123","name":"inspect_pipeline"},"output_index":0}',
    'event: response.function_call_arguments.delta\ndata: {"delta":"{}","item_id":"fc_123","output_index":0}',
    'event: response.function_call_arguments.done\ndata: {"arguments":"{}","item_id":"fc_123","output_index":0}',
    'event: response.output_item.done\ndata: {"item":{"id":"fc_123","type":"function_call","status":"completed","arguments":"{}","call_id":"call_123","name":"inspect_pipeline"},"output_index":0}',
    'event: response.completed\ndata: {"response":{"status":"completed","output":[]}}',
    ""
  ].join("\n\n"), { status: 200, headers: { "Content-Type": "text/event-stream" } }));
  try {
    const result = await createChatCompletion({
      state_dir: stateDir,
      llm_base_url: "https://api.openai.com/v1",
      llm_api_key: "",
      llm_model: "gpt-5.4-mini"
    }, [{ role: "user", content: "Status?" }], [{
      type: "function",
      function: { name: "inspect_pipeline", parameters: {} }
    }]);

    assert.equal(result.choices[0].message.content, "");
    assert.equal(result.choices[0].message.tool_calls[0].id, "call_123");
    assert.equal(result.choices[0].message.tool_calls[0].function.name, "inspect_pipeline");
    assert.equal(result.choices[0].message.tool_calls[0].function.arguments, "{}");
  } finally {
    restore();
    rmSync(stateDir, { recursive: true, force: true });
  }
});

test("createChatCompletion falls back to the API key when the OAuth backend rejects the request", async () => {
  const stateDir = createStateDir();
  const calls = [];
  await saveToken(stateDir, healthyToken());
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    if (calls.length === 1) {
      return new Response('{"error":"oauth denied"}', { status: 401, headers: { "Content-Type": "application/json" } });
    }
    return jsonResponse(200, { choices: [{ message: { role: "assistant", content: "api fallback ok" } }] });
  });
  try {
    const result = await createChatCompletion({
      state_dir: stateDir,
      llm_base_url: "https://api.openai.com/v1",
      llm_api_key: "sk-fallback",
      llm_model: "gpt-4.1"
    }, [{ role: "user", content: "Hallo" }]);

    assert.equal(calls[0].url, "https://chatgpt.com/backend-api/codex/responses");
    assert.equal(calls[1].url, "https://api.openai.com/v1/chat/completions");
    assert.equal(result.choices[0].message.content, "api fallback ok");
  } finally {
    restore();
    rmSync(stateDir, { recursive: true, force: true });
  }
});
