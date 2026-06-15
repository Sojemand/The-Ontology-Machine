import { messageText } from "./adapter_core.js";

export function googleBody(messages, { model, tools } = {}) {
  const systemText = [];
  const contents = [];
  for (const message of Array.isArray(messages) ? messages : []) {
    const role = String(message?.role || "user").toLowerCase();
    if (role === "system") {
      systemText.push(messageText(message));
    } else {
      contents.push({ role: role === "assistant" ? "model" : "user", parts: [{ text: messageText(message) }] });
    }
  }
  const declarations = googleToolDeclarations(tools);
  return {
    contents: contents.length ? contents : [{ role: "user", parts: [{ text: "" }] }],
    ...(systemText.length ? { systemInstruction: { parts: [{ text: systemText.join("\n\n") }] } } : {}),
    ...(declarations.length ? { tools: [{ functionDeclarations: declarations }] } : {}),
    generationConfig: { maxOutputTokens: 4096 },
    model
  };
}

export function normalizeGooglePayload(payload) {
  const parts = payload?.candidates?.[0]?.content?.parts || [];
  const text = parts.filter((part) => part.text).map((part) => part.text).join("");
  const tool_calls = parts.filter((part) => part.functionCall?.name).map((part, index) => ({
    id: `google_tool_${index + 1}`,
    type: "function",
    function: { name: String(part.functionCall.name || ""), arguments: JSON.stringify(part.functionCall.args || {}) }
  }));
  return { choices: [{ message: { role: "assistant", content: text, ...(tool_calls.length ? { tool_calls } : {}) } }] };
}

export function googleEmbeddingRequests(modelId, input) {
  const values = Array.isArray(input) ? input : [input];
  return values.map((text) => ({ model: `models/${modelId}`, content: { parts: [{ text: String(text || "") }] } }));
}

function googleToolDeclarations(tools = []) {
  return (Array.isArray(tools) ? tools : [])
    .map((tool) => tool?.function ? {
      name: tool.function.name,
      description: tool.function.description || "",
      parameters: tool.function.parameters || {}
    } : null)
    .filter(Boolean);
}
