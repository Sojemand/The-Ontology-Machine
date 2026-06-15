import { estimateMessagesTokens, estimateTokens } from "./tokens.js";

export function createEstimatedTokenUsageTracker() {
  const totals = {
    estimated: true,
    input_tokens: 0,
    output_tokens: 0,
    llm_calls: 0
  };
  return {
    recordInput(messages) {
      totals.input_tokens += estimateMessagesTokens(messages);
      totals.llm_calls += 1;
    },
    recordAssistantMessage(message) {
      totals.output_tokens += estimateAssistantOutputTokens(message);
    },
    snapshot() {
      return { ...totals };
    }
  };
}

export function estimateAssistantOutputTokens(message) {
  let total = estimateTokens(message?.content || "");
  for (const toolCall of Array.isArray(message?.tool_calls) ? message.tool_calls : []) {
    total += 4;
    total += estimateTokens(toolCall?.function?.name || "");
    total += estimateTokens(toolCall?.function?.arguments || "");
  }
  return total;
}

export function normalizeTokenUsage(value) {
  return {
    estimated: value?.estimated !== false,
    input_tokens: Math.max(0, Math.round(Number(value?.input_tokens) || 0)),
    output_tokens: Math.max(0, Math.round(Number(value?.output_tokens) || 0)),
    llm_calls: Math.max(0, Math.round(Number(value?.llm_calls) || 0))
  };
}
