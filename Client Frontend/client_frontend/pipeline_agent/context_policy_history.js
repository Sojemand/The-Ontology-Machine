import { computeHistoryBudget } from "../min_agent.js";
import { estimateMessagesTokens } from "../tokens.js";
import {
  KERNEL_HISTORY_PREFIX,
  PIPELINE_HISTORY_ENTRY_CHAR_LIMIT,
  PIPELINE_HISTORY_TOKEN_CAP,
  PIPELINE_RESPONSE_RESERVE_TOKENS
} from "./context_policy_constants.js";
import { clipMiddle } from "./context_policy_core.js";
import { compactKernelMirrorEvent, historyEntryMirrorEvent } from "./context_policy_kernel_events.js";
import { estimateToolsTokens } from "./context_policy_tool_results.js";

export function trimPipelineHistoryForContext(history, contextLimit, frontendPolicy, reservedTokens) {
  const normalized = normalizePipelineHistory(history);
  const configuredBudget = computeHistoryBudget(contextLimit, frontendPolicy);
  const contextBudget = Math.max(0, (Number(contextLimit) || 127_096) - Math.max(0, reservedTokens || 0));
  const budget = Math.max(0, Math.min(configuredBudget, PIPELINE_HISTORY_TOKEN_CAP, contextBudget));
  const trimmed = [];
  let totalTokens = 0;
  for (let index = normalized.length - 1; index >= 0; index -= 1) {
    const entry = normalized[index];
    const providerEntry = toProviderMessage(entry);
    const entryTokens = estimateMessagesTokens([providerEntry]) + 4;
    if (trimmed.length > 0 && totalTokens + entryTokens > budget) break;
    if (trimmed.length === 0 && entryTokens > budget) {
      const clipped = clipMiddle(entry.content, Math.max(500, Math.floor(budget * 3)));
      trimmed.unshift(entry.role === "kernel" ? { ...entry, content: clipped } : { role: entry.role, content: clipped });
      break;
    }
    totalTokens += entryTokens;
    trimmed.unshift(entry);
  }
  return trimmed;
}

export function trimWorkingMessagesForProvider(messages, tools, contextLimit) {
  const providerMessages = (Array.isArray(messages) ? messages : []).map(toProviderMessage).filter(Boolean);
  const toolTokens = estimateToolsTokens(tools);
  const available = Math.max(4_000, (Number(contextLimit) || 127_096) - toolTokens - PIPELINE_RESPONSE_RESERVE_TOKENS);
  if (estimateMessagesTokens(providerMessages) <= available) return providerMessages;
  const systemMessage = providerMessages[0];
  const kept = [];
  let total = estimateMessagesTokens([systemMessage]);
  for (let index = providerMessages.length - 1; index >= 1; index -= 1) {
    const entry = providerMessages[index];
    const entryTokens = estimateMessagesTokens([entry]);
    if (kept.length > 0 && total + entryTokens > available) break;
    total += entryTokens;
    kept.unshift(entry);
  }
  return [systemMessage, ...kept];
}

function normalizePipelineHistory(history) {
  return (Array.isArray(history) ? history : [])
    .filter((entry) => entry && (entry.role === "user" || entry.role === "assistant" || entry.role === "kernel"))
    .map(normalizeHistoryEntry)
    .filter((entry) => entry.role === "kernel" || entry.content);
}

function normalizeHistoryEntry(entry) {
  if (entry.role === "kernel") {
    const compactMirror = compactKernelMirrorEvent(entry.kernel_mirror_event || historyEntryMirrorEvent(entry));
    const content = String(entry.content || JSON.stringify(compactMirror)).replace(/\r\n/g, "\n").trim();
    return {
      role: "kernel",
      content: clipMiddle(content, PIPELINE_HISTORY_ENTRY_CHAR_LIMIT),
      kernel_mirror_event: compactMirror
    };
  }
  return {
    role: entry.role,
    content: clipMiddle(
      String(entry.content || "").replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim(),
      PIPELINE_HISTORY_ENTRY_CHAR_LIMIT
    )
  };
}

function toProviderMessage(entry) {
  if (!entry || typeof entry !== "object") return null;
  if (entry.role === "kernel") {
    const compact = compactKernelMirrorEvent(entry.kernel_mirror_event || {});
    return { role: "system", content: `${KERNEL_HISTORY_PREFIX}\n${JSON.stringify(compact)}` };
  }
  return { role: entry.role, content: String(entry.content || "") };
}
