import { randomUUID } from "node:crypto";

import {
  summarizeAssistantMessage,
  summarizeMessages,
  summarizeToolArguments,
  summarizeToolResult
} from "./call_logger.js";

export function createQueryTurnId() {
  return `qry_${Date.now().toString(36)}_${randomUUID().slice(0, 8)}`;
}

function errorSummary(error) {
  return {
    name: error?.name || "",
    message: error instanceof Error ? error.message : String(error || "Unknown error.")
  };
}

function runtimeSummary(runtimeConfig) {
  return {
    provider: runtimeConfig?.llm_provider || runtimeConfig?.provider || "",
    model: runtimeConfig?.llm_model || runtimeConfig?.model || ""
  };
}

function toolRequestSummary(tools) {
  const toolList = Array.isArray(tools) ? tools : [];
  return {
    tool_count: toolList.length,
    tool_names: toolList.map((tool) => tool?.function?.name || "").filter(Boolean),
    tool_choice: toolList.length ? "auto" : "none"
  };
}

export async function logTurnStart(callLogger, { turnId, userMessage, history, corpusDocCount, runtimeConfig }) {
  await callLogger.record({
    event: "turn_start",
    turn_id: turnId,
    user_message_chars: String(userMessage || "").length,
    history_count: Array.isArray(history) ? history.length : 0,
    corpus_documents: corpusDocCount,
    runtime: runtimeSummary(runtimeConfig)
  });
}

export async function runLoggedLlmCall(callLogger, { turnId, round, runtimeConfig, messages, tools, createChatCompletionFn }) {
  const startedAt = Date.now();
  await callLogger.record({
    event: "llm_call_start",
    turn_id: turnId,
    round,
    runtime: runtimeSummary(runtimeConfig),
    request: toolRequestSummary(tools),
    context: summarizeMessages(messages)
  });
  try {
    const assistantMessage = (await createChatCompletionFn(runtimeConfig, messages, tools))?.choices?.[0]?.message || null;
    await callLogger.record({
      event: "llm_call_end",
      turn_id: turnId,
      round,
      duration_ms: Date.now() - startedAt,
      assistant: summarizeAssistantMessage(assistantMessage)
    });
    return assistantMessage;
  } catch (error) {
    await callLogger.record({
      event: "llm_call_error",
      turn_id: turnId,
      round,
      duration_ms: Date.now() - startedAt,
      runtime: runtimeSummary(runtimeConfig),
      error: errorSummary(error)
    });
    throw error;
  }
}

export async function logToolCallStart(callLogger, { turnId, round, toolIndex, toolCall }) {
  await callLogger.record({
    event: "tool_call_start",
    turn_id: turnId,
    round,
    tool_index: toolIndex,
    tool_call_id: toolCall?.id || "",
    tool_name: toolCall?.function?.name || "",
    arguments: summarizeToolArguments(toolCall)
  });
}

export async function logToolCallEnd(callLogger, { turnId, round, toolIndex, toolCall, startedAt, result, resultDocIds }) {
  await callLogger.record({
    event: "tool_call_end",
    turn_id: turnId,
    round,
    tool_index: toolIndex,
    tool_call_id: toolCall?.id || "",
    tool_name: toolCall?.function?.name || "",
    duration_ms: Date.now() - startedAt,
    result: summarizeToolResult(result),
    doc_id_count: Array.isArray(resultDocIds) ? resultDocIds.length : 0,
    doc_ids_preview: Array.isArray(resultDocIds) ? resultDocIds.slice(0, 20) : []
  });
}

export async function logToolCallError(callLogger, { turnId, round, toolIndex, toolCall, startedAt, error }) {
  await callLogger.record({
    event: "tool_call_error",
    turn_id: turnId,
    round,
    tool_index: toolIndex,
    tool_call_id: toolCall?.id || "",
    tool_name: toolCall?.function?.name || "",
    duration_ms: Date.now() - startedAt,
    error: errorSummary(error)
  });
}

export async function logTurnFinal(callLogger, { turnId, round, answer, sourceCount, tokenUsage }) {
  await callLogger.record({
    event: "turn_final",
    turn_id: turnId,
    round,
    answer_chars: String(answer || "").length,
    source_count: sourceCount,
    exactness: sourceCount ? "evidence_grounded" : "insufficient_evidence",
    token_usage: tokenUsage
  });
}

export async function logTurnError(callLogger, { turnId, round, message, maxRounds }) {
  await callLogger.record({
    event: "turn_error",
    turn_id: turnId,
    round,
    error: { message },
    max_rounds: maxRounds
  });
}
