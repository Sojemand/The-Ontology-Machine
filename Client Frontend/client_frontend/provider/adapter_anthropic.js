import { messageText } from "./adapter_core.js";

export const ANTHROPIC_VERSION = "2023-06-01";

export function anthropicBody(messages, { model, temperature, tools } = {}) {
  const system = [];
  const bodyMessages = [];
  for (const message of Array.isArray(messages) ? messages : []) {
    const role = String(message?.role || "user").toLowerCase();
    if (role === "system") {
      system.push(messageText(message));
    } else {
      bodyMessages.push({ role: role === "assistant" ? "assistant" : "user", content: messageText(message) });
    }
  }
  const convertedTools = anthropicTools(tools);
  return {
    model,
    max_tokens: 4096,
    temperature,
    ...(system.length ? { system: system.join("\n\n") } : {}),
    messages: bodyMessages.length ? bodyMessages : [{ role: "user", content: "" }],
    ...(convertedTools.length ? { tools: convertedTools } : {})
  };
}

export function normalizeAnthropicPayload(payload) {
  const content = Array.isArray(payload?.content) ? payload.content : [];
  const text = content.filter((part) => part?.type === "text").map((part) => part.text || "").join("");
  const tool_calls = content.filter((part) => part?.type === "tool_use").map((part) => ({
    id: String(part.id || part.name),
    type: "function",
    function: { name: String(part.name || ""), arguments: JSON.stringify(part.input || {}) }
  }));
  return { choices: [{ message: { role: "assistant", content: text, ...(tool_calls.length ? { tool_calls } : {}) } }] };
}

function anthropicTools(tools = []) {
  return tools.map((tool) => tool?.function ? {
    name: tool.function.name,
    description: tool.function.description || "",
    input_schema: tool.function.parameters || {}
  } : tool).filter((tool) => tool?.name);
}
