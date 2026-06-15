import { messageText } from "./adapter_core.js";

export function openAiChatBody(messages, { model, temperature, tools, toolChoice = "auto" } = {}) {
  return {
    model,
    temperature,
    max_completion_tokens: 4096,
    messages,
    ...(Array.isArray(tools) && tools.length ? { tools, tool_choice: toolChoice, parallel_tool_calls: true } : {})
  };
}

export function responsesBody(messages, { model, tools } = {}) {
  const { instructions, input } = responseInputItems(messages);
  const convertedTools = responsesTools(tools);
  return {
    model,
    instructions: instructions.join("\n\n") || "Respond helpfully and use tools when needed.",
    input: input.length ? input : [{ role: "user", content: [{ type: "input_text", text: "" }] }],
    max_output_tokens: 4096,
    store: false,
    ...(convertedTools.length ? { tools: convertedTools, tool_choice: "auto", parallel_tool_calls: true } : {})
  };
}

export function normalizeResponsesPayload(payload) {
  if (payload?.choices?.length) return payload;
  const output = Array.isArray(payload?.output) ? payload.output : [];
  const content = output.flatMap((item) => Array.isArray(item?.content) ? item.content : []).find((part) => part?.type === "output_text")?.text || payload?.output_text || "";
  const tool_calls = output.filter((item) => item?.type === "function_call" && item?.name).map((item, index) => ({
    id: String(item.call_id || item.id || `tool_${index + 1}`),
    type: "function",
    function: { name: String(item.name || ""), arguments: typeof item.arguments === "string" ? item.arguments : JSON.stringify(item.arguments || {}) }
  }));
  return { choices: [{ message: { role: "assistant", content, ...(tool_calls.length ? { tool_calls } : {}) } }] };
}

function responsesTools(tools = []) {
  return (Array.isArray(tools) ? tools : [])
    .map((tool) => tool?.type === "function" && tool.function ? responseFunctionTool(tool.function) : tool)
    .filter((tool) => tool?.type !== "function" || String(tool?.name || "").trim());
}

function responseFunctionTool(fn) {
  return {
    type: "function",
    name: String(fn.name || ""),
    description: String(fn.description || ""),
    parameters: fn.parameters || { type: "object", properties: {}, additionalProperties: false },
    ...(fn.strict !== undefined ? { strict: fn.strict } : {})
  };
}

function responseInputItems(messages = []) {
  const instructions = [];
  const input = [];
  for (const message of Array.isArray(messages) ? messages : []) {
    appendResponseInput(message, instructions, input);
  }
  return { instructions, input };
}

function appendResponseInput(message, instructions, input) {
  const role = String(message?.role || "user").toLowerCase();
  if (role === "system") {
    const text = messageText(message);
    if (text) instructions.push(text);
    return;
  }
  if (role === "tool") {
    const callId = String(message?.tool_call_id || "").trim();
    input.push(callId ? { type: "function_call_output", call_id: callId, output: String(message?.content || "") } : responseMessage("user", messageText(message)));
    return;
  }
  if (role === "assistant") {
    const content = typeof message?.content === "string" ? message.content.trim() : "";
    if (content) input.push(responseMessage("assistant", content));
    input.push(...responseFunctionCalls(message?.tool_calls));
    if (!content && !message?.tool_calls?.length) input.push(responseMessage("assistant", messageText(message)));
    return;
  }
  input.push(responseMessage("user", messageText(message)));
}

function responseMessage(role, text) {
  const normalizedRole = role === "assistant" ? "assistant" : "user";
  return {
    role: normalizedRole,
    content: [{ type: normalizedRole === "assistant" ? "output_text" : "input_text", text }]
  };
}

function responseFunctionCalls(toolCalls = []) {
  return (Array.isArray(toolCalls) ? toolCalls : [])
    .map((toolCall, index) => {
      const name = String(toolCall?.function?.name || "").trim();
      if (!name) return null;
      return {
        type: "function_call",
        call_id: String(toolCall?.id || `tool_${index + 1}`),
        name,
        arguments: typeof toolCall?.function?.arguments === "string" ? toolCall.function.arguments : JSON.stringify(toolCall?.function?.arguments || {})
      };
    })
    .filter(Boolean);
}
