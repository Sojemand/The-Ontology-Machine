import { randomUUID } from "node:crypto";

import {
  summarizeAssistantMessage,
  summarizeMessages,
  summarizeToolArguments,
  summarizeToolResult
} from "./call_logger.js";
import { docIdsFromToolResult } from "./workflow_tools.js";

export function createOntologyTurnId() {
  return `ont_${Date.now().toString(36)}_${randomUUID().slice(0, 8)}`;
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

function toolRequestSummary(runtimeConfig, tools) {
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
  const inputTokens = summarizeMessages(messages);
  await callLogger.record({
    event: "llm_call_start",
    turn_id: turnId,
    round,
    runtime: runtimeSummary(runtimeConfig),
    request: toolRequestSummary(runtimeConfig, tools),
    context: inputTokens
  });
  try {
    const assistantMessage = (await createChatCompletionFn(runtimeConfig, messages, tools))?.choices?.[0]?.message || null;
    const assistantSummary = summarizeAssistantMessage(assistantMessage);
    await callLogger.record({
      event: "llm_call_end",
      turn_id: turnId,
      round,
      duration_ms: Date.now() - startedAt,
      assistant: assistantSummary
    });
    return assistantMessage;
  } catch (error) {
    await callLogger.record({
      event: "llm_call_error",
      turn_id: turnId,
      round,
      duration_ms: Date.now() - startedAt,
      error: errorSummary(error)
    });
    throw error;
  }
}

export async function runLoggedToolCall(callLogger, { turnId, round, toolIndex, toolCall, execute }) {
  const startedAt = Date.now();
  const toolName = toolCall?.function?.name || "";
  await callLogger.record({
    event: "tool_call_start",
    turn_id: turnId,
    round,
    tool_index: toolIndex,
    tool_call_id: toolCall?.id || "",
    tool_name: toolName,
    arguments: summarizeToolArguments(toolCall)
  });
  try {
    const result = await execute();
    const resultDocIds = docIdsFromToolResult(result);
    await callLogger.record({
      event: "tool_call_end",
      turn_id: turnId,
      round,
      tool_index: toolIndex,
      tool_call_id: toolCall?.id || "",
      tool_name: toolName,
      duration_ms: Date.now() - startedAt,
      result: summarizeToolResult(result),
      doc_id_count: resultDocIds.length,
      doc_ids_preview: resultDocIds.slice(0, 20)
    });
    return { result, resultDocIds };
  } catch (error) {
    await callLogger.record({
      event: "tool_call_error",
      turn_id: turnId,
      round,
      tool_index: toolIndex,
      tool_call_id: toolCall?.id || "",
      tool_name: toolName,
      duration_ms: Date.now() - startedAt,
      error: errorSummary(error)
    });
    throw error;
  }
}

export async function logTurnFinal(callLogger, { turnId, round, answer, sourceCount }) {
  await callLogger.record({
    event: "turn_final",
    turn_id: turnId,
    round,
    answer_chars: String(answer || "").length,
    source_count: sourceCount,
    exactness: sourceCount ? "evidence_grounded" : "insufficient_evidence"
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
