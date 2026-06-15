import assert from "node:assert/strict";
import test from "node:test";

import { providerRuntime } from "../../client_frontend/provider/policy.js";
import { ContextLengthError, createChatCompletion } from "../../server/provider.js";

import { jsonResponse, mockFetch } from "./provider-surface-support.js";

const EXPECTED_PROVIDER_FAMILIES = {
  openai: "openai_responses",
  anthropic: "anthropic_messages",
  google: "google_gemini",
  xai: "openai_responses",
  openrouter: "openai_chat",
  groq: "openai_responses",
  together: "openai_chat",
  fireworks: "openai_chat",
  mistral: "openai_chat",
  deepseek: "openai_chat",
  sambanova: "openai_chat",
  cerebras: "openai_chat",
  mammouth: "openai_chat",
  lmstudio: "openai_chat",
  ollama: "openai_chat",
  openai_compat: "openai_chat"
};

test("provider catalog maps selectable providers to the intended request family", () => {
  for (const [provider, family] of Object.entries(EXPECTED_PROVIDER_FAMILIES)) {
    assert.equal(providerRuntime(provider).family, family, provider);
  }
});

test("createChatCompletion forwards runtime config, messages and tools", async () => {
  const calls = [];
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    return jsonResponse(200, {
      choices: [{ message: { role: "assistant", content: "ok" } }]
    });
  });
  try {
    const runtimeConfig = { llm_base_url: "https://api.openai.com/v1/", llm_api_key: "sk-test", llm_model: "gpt-4.1" };
    const messages = [{ role: "user", content: "Hallo" }];
    const tools = [{ type: "function", function: { name: "sql_query", parameters: {} } }];
    const result = await createChatCompletion(runtimeConfig, messages, tools);
    const request = calls.at(0);
    const body = JSON.parse(request.init.body);
    assert.equal(request.url, "https://api.openai.com/v1/chat/completions");
    assert.equal(request.init.headers.Authorization, "Bearer sk-test");
    assert.equal(body.model, "gpt-4.1");
    assert.equal(body.temperature, 0.2);
    assert.deepEqual(body.messages, messages);
    assert.deepEqual(body.tools, tools);
    assert.equal(body.tool_choice, "auto");
    assert.equal(body.parallel_tool_calls, true);
    assert.equal(result.choices[0].message.content, "ok");
  } finally {
    restore();
  }
});

test("createChatCompletion sends OpenRouter through chat completions", async () => {
  const calls = [];
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    return jsonResponse(200, {
      choices: [{ message: { role: "assistant", content: "openrouter ok" } }]
    });
  });
  try {
    const runtimeConfig = {
      llm_provider: "openrouter",
      llm_base_url: "https://openrouter.ai/api/v1/",
      llm_api_key: "sk-or-test",
      llm_model: "openrouter/owl-alpha"
    };
    const messages = [{ role: "user", content: "Hallo" }];
    const tools = [{ type: "function", function: { name: "sql_query", parameters: {} } }];
    const result = await createChatCompletion(runtimeConfig, messages, tools);
    const request = calls.at(0);
    const body = JSON.parse(request.init.body);

    assert.equal(request.url, "https://openrouter.ai/api/v1/chat/completions");
    assert.equal(body.model, "openrouter/owl-alpha");
    assert.deepEqual(body.messages, messages);
    assert.deepEqual(body.tools, tools);
    assert.equal(body.tool_choice, "auto");
    assert.equal(result.choices[0].message.content, "openrouter ok");
  } finally {
    restore();
  }
});

test("createChatCompletion converts chat tools for the OpenAI Responses API", async () => {
  const calls = [];
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    return jsonResponse(200, {
      output: [{ type: "message", content: [{ type: "output_text", text: "responses ok" }] }]
    });
  });
  try {
    const tools = [{
      type: "function",
      function: {
        name: "inspect_pipeline",
        description: "Inspect pipeline state.",
        parameters: { type: "object", properties: {}, additionalProperties: false }
      }
    }];
    const result = await createChatCompletion({
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1/",
      llm_api_key: "sk-test",
      llm_model: "gpt-4.1"
    }, [
      { role: "user", content: "Ich will eine neue DBV erstellen." },
      { role: "assistant", content: "Gern, welches Ziel und welcher Ordner?" },
      { role: "user", content: "Status?" }
    ], tools);
    const body = JSON.parse(calls.at(0).init.body);

    assert.equal(calls.at(0).url, "https://api.openai.com/v1/responses");
    assert.equal(body.input[0].content[0].type, "input_text");
    assert.equal(body.input[1].role, "assistant");
    assert.equal(body.input[1].content[0].type, "output_text");
    assert.deepEqual(body.tools, [{
      type: "function",
      name: "inspect_pipeline",
      description: "Inspect pipeline state.",
      parameters: { type: "object", properties: {}, additionalProperties: false }
    }]);
    assert.equal(body.tools[0].function, undefined);
    assert.equal(body.tool_choice, "auto");
    assert.equal(result.choices[0].message.content, "responses ok");
  } finally {
    restore();
  }
});

test("createChatCompletion sends Responses tool-call rounds as function call items", async () => {
  const calls = [];
  const restore = mockFetch((url, init) => {
    calls.push({ url, init });
    return jsonResponse(200, {
      output: [{ type: "message", content: [{ type: "output_text", text: "tool round ok" }] }]
    });
  });
  try {
    await createChatCompletion({
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1",
      llm_api_key: "sk-test",
      llm_model: "gpt-4.1"
    }, [
      { role: "user", content: "Neue DBV" },
      { role: "assistant", content: "", tool_calls: [{ id: "call-1", type: "function", function: { name: "inspect_pipeline", arguments: "{}" } }] },
      { role: "tool", tool_call_id: "call-1", content: "{\"status\":\"ok\"}" }
    ], [{ type: "function", function: { name: "inspect_pipeline", parameters: {} } }]);
    const body = JSON.parse(calls.at(0).init.body);

    assert.deepEqual(body.input[1], { type: "function_call", call_id: "call-1", name: "inspect_pipeline", arguments: "{}" });
    assert.deepEqual(body.input[2], { type: "function_call_output", call_id: "call-1", output: "{\"status\":\"ok\"}" });
  } finally {
    restore();
  }
});

test("createChatCompletion preserves Responses call_id for tool output routing", async () => {
  const restore = mockFetch(() => jsonResponse(200, {
    output: [{
      type: "function_call",
      id: "fc_123",
      call_id: "call_pipeline_123",
      name: "inspect_pipeline",
      arguments: "{}"
    }]
  }));
  try {
    const result = await createChatCompletion({
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1",
      llm_api_key: "sk-test",
      llm_model: "gpt-4.1"
    }, [{ role: "user", content: "Status?" }], [{ type: "function", function: { name: "inspect_pipeline", parameters: {} } }]);

    assert.equal(result.choices[0].message.tool_calls[0].id, "call_pipeline_123");
    assert.equal(result.choices[0].message.tool_calls[0].function.name, "inspect_pipeline");
  } finally {
    restore();
  }
});

test("createChatCompletion classifies context-length provider errors", async () => {
  const restore = mockFetch(() => jsonResponse(400, {
    error: { message: "maximum context length exceeded" }
  }));
  try {
    await assert.rejects(
      () => createChatCompletion({
        llm_base_url: "https://api.openai.com/v1",
        llm_api_key: "sk-test",
        llm_model: "gpt-4.1"
      }, [{ role: "user", content: "Hallo" }]),
      (error) => error instanceof ContextLengthError && /maximum context length exceeded/.test(error.message)
    );
  } finally {
    restore();
  }
});
