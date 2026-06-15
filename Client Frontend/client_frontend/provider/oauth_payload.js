function messageText(message) {
  const content = typeof message?.content === "string" ? message.content : Array.isArray(message?.content) ? JSON.stringify(message.content) : "";
  const toolCalls = Array.isArray(message?.tool_calls) && message.tool_calls.length ? `\n[tool_calls]\n${JSON.stringify(message.tool_calls)}` : "";
  if (message?.role === "tool") {
    return `[tool_result ${message.tool_call_id || ""}]\n${content}`;
  }
  return `${content}${toolCalls}`.trim();
}

function responsesTools(tools = []) {
  return (Array.isArray(tools) ? tools : [])
    .map((tool) => {
      if (tool?.type === "function" && tool.function) {
        const fn = tool.function || {};
        return {
          type: "function",
          name: String(fn.name || ""),
          description: String(fn.description || ""),
          parameters: fn.parameters || { type: "object", properties: {}, additionalProperties: false },
          ...(fn.strict !== undefined ? { strict: fn.strict } : {})
        };
      }
      return tool;
    })
    .filter((tool) => tool?.type !== "function" || String(tool?.name || "").trim());
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

function responseInputItems(messages = []) {
  const instructions = [];
  const input = [];
  for (const message of Array.isArray(messages) ? messages : []) {
    const role = String(message?.role || "user").trim().toLowerCase();
    if (role === "system") {
      const text = messageText(message);
      if (text) instructions.push(text);
      continue;
    }
    if (role === "tool") {
      const callId = String(message?.tool_call_id || "").trim();
      if (callId) {
        input.push({ type: "function_call_output", call_id: callId, output: String(message?.content || "") });
      } else {
        input.push(responseMessage("user", messageText(message)));
      }
      continue;
    }
    if (role === "assistant") {
      const content = typeof message?.content === "string" ? message.content.trim() : "";
      if (content) input.push(responseMessage("assistant", content));
      input.push(...responseFunctionCalls(message?.tool_calls));
      if (!content && !message?.tool_calls?.length) input.push(responseMessage("assistant", messageText(message)));
      continue;
    }
    input.push(responseMessage("user", messageText(message)));
  }
  return { instructions, input };
}

export function buildBackendPayload(messages, { model, tools } = {}) {
  const { instructions, input } = responseInputItems(messages);
  const convertedTools = responsesTools(tools);
  return {
    model,
    instructions: instructions.join("\n\n") || "Respond helpfully and use tools when needed.",
    input: input.length ? input : [{ role: "user", content: [{ type: "input_text", text: "" }] }],
    reasoning: { effort: "none" },
    stream: true,
    ...(convertedTools.length ? { tools: convertedTools, tool_choice: "auto", parallel_tool_calls: true } : {}),
    store: false
  };
}
