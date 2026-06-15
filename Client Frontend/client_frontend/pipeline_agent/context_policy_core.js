export function parseToolArguments(toolCall) {
  try {
    const parsed = JSON.parse(toolCall?.function?.arguments || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function assistantText(message) {
  if (typeof message?.content === "string") return message.content.trim();
  if (!Array.isArray(message?.content)) return "";
  return message.content.map((item) => item?.text || "").filter(Boolean).join("\n").trim();
}

export function toChatTool(tool) {
  return {
    type: "function",
    function: {
      name: String(tool.name || ""),
      description: String(tool.description || ""),
      parameters: tool.inputSchema || { type: "object", properties: {}, additionalProperties: false }
    }
  };
}

export function clipMiddle(text, maxChars) {
  const value = String(text || "");
  if (!Number.isFinite(maxChars) || maxChars < 1 || value.length <= maxChars) return value;
  const marker = "\n...[truncated for model context]...\n";
  const edge = Math.max(1, Math.floor((maxChars - marker.length) / 2));
  return `${value.slice(0, edge)}${marker}${value.slice(-edge)}`;
}
