import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { estimateAssistantOutputTokens } from "../token_usage.js";

export const QUERY_AGENT_CALL_LOG_FILE = "query_agent_call_log.json";
const DEFAULT_MAX_ENTRIES = 100;
const MAX_TEXT_CHARS = 1200;
const MAX_SQL_CHARS = 700;

function nowIso() {
  return new Date().toISOString();
}

function trimText(value, maxChars = MAX_TEXT_CHARS) {
  const text = String(value ?? "");
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars)}...[truncated ${text.length - maxChars} chars]`;
}

function safeJsonParse(text) {
  try {
    return { ok: true, value: JSON.parse(String(text || "{}")) };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "JSON parse failed." };
  }
}

function jsonCharCount(value) {
  try {
    return JSON.stringify(value).length;
  } catch {
    return 0;
  }
}

function countArray(value) {
  return Array.isArray(value) ? value.length : undefined;
}

function compactObjectKeys(value) {
  return value && typeof value === "object" ? Object.keys(value).slice(0, 30) : [];
}

export function summarizeToolArguments(toolCall) {
  const toolName = toolCall?.function?.name || "";
  const rawArguments = toolCall?.function?.arguments || "{}";
  const parsed = safeJsonParse(rawArguments);
  if (!parsed.ok) {
    return {
      parse_error: parsed.error,
      raw_chars: String(rawArguments).length,
      raw_preview: trimText(rawArguments, 500)
    };
  }
  const args = parsed.value || {};
  if (toolName === "sql_query") return { query: trimText(args.query || "", MAX_SQL_CHARS) };
  if (toolName === "semantic_search") return { text: trimText(args.text || "", 500), limit: args.limit };
  if (toolName.startsWith("get_document")) return { doc_id: args.doc_id, view_tool: toolName };
  if (toolName === "get_provenance") return { doc_id: args.doc_id, target: trimText(args.target || "", 240), target_kind: args.target_kind };
  if (toolName === "database_coverage_snapshot") return { focus: args.focus, limit: args.limit };
  if (toolName === "list_source_documents") return { limit: args.limit };
  if (toolName === "get_source_document") return { source_document_id: args.source_document_id, doc_id: args.doc_id, limit: args.limit };
  if (toolName === "list_ontology_lenses") return { include_archived: args.include_archived, limit: args.limit };
  if (toolName === "get_ontology_lens") return { ontology_id: args.ontology_id, limit: args.limit };
  if (toolName === "workbench") {
    return {
      runtime: args.runtime,
      timeout_ms: args.timeout_ms,
      code_chars: String(args.code || "").length,
      code_preview: trimText(args.code || "", 700)
    };
  }
  return {
    keys: compactObjectKeys(args),
    json_chars: jsonCharCount(args),
    preview: trimText(JSON.stringify(args), 900)
  };
}

export function summarizeToolResult(result) {
  return {
    ok: result?.ok,
    available: result?.available,
    found: result?.found,
    error: result?.error ? trimText(result.error, 700) : undefined,
    reason: result?.reason ? trimText(result.reason, 500) : undefined,
    truncated: result?.truncated,
    keys: compactObjectKeys(result),
    row_counts: {
      rows: countArray(result?.rows),
      results: countArray(result?.results),
      sources: countArray(result?.sources),
      fallback_rows: countArray(result?.fallback?.rows),
      fallback_results: countArray(result?.fallback?.results),
      pages_rows: countArray(result?.pages?.rows),
      lenses: countArray(result?.lenses),
      nodes: countArray(result?.nodes),
      edges: countArray(result?.edges),
      assertions: countArray(result?.assertions)
    },
    json_chars: jsonCharCount(result)
  };
}

export function summarizeMessages(messages) {
  let contentChars = 0;
  let toolResultChars = 0;
  let toolResultCount = 0;
  const roles = {};
  for (const message of Array.isArray(messages) ? messages : []) {
    roles[message?.role || "unknown"] = (roles[message?.role || "unknown"] || 0) + 1;
    const content = typeof message?.content === "string" ? message.content : JSON.stringify(message?.content || "");
    contentChars += content.length;
    if (message?.tool_calls) contentChars += jsonCharCount(message.tool_calls);
    if (message?.role === "tool") {
      toolResultCount += 1;
      toolResultChars += content.length;
    }
  }
  return {
    message_count: Array.isArray(messages) ? messages.length : 0,
    roles,
    content_chars: contentChars,
    approx_tokens: Math.ceil(contentChars / 4),
    tool_result_count: toolResultCount,
    tool_result_chars: toolResultChars
  };
}

export function summarizeAssistantMessage(message) {
  const toolCalls = Array.isArray(message?.tool_calls) ? message.tool_calls : [];
  const toolArgumentChars = toolCalls.reduce((total, toolCall) => total + String(toolCall?.function?.arguments || "").length, 0);
  return {
    content_chars: String(message?.content || "").length,
    tool_call_count: toolCalls.length,
    tool_names: toolCalls.map((toolCall) => toolCall?.function?.name || "").filter(Boolean),
    tool_argument_chars: toolArgumentChars,
    approx_output_tokens: estimateAssistantOutputTokens(message)
  };
}

export async function readQueryCallLog(logPath) {
  try {
    const parsed = JSON.parse(await readFile(logPath, "utf8"));
    return { ...parsed, entries: Array.isArray(parsed?.entries) ? parsed.entries : [] };
  } catch {
    return { version: 1, max_entries: DEFAULT_MAX_ENTRIES, updated_at: "", entries: [] };
  }
}

export function createQueryCallLogger({ stateRoot, maxEntries = DEFAULT_MAX_ENTRIES } = {}) {
  const normalizedMaxEntries = Math.max(1, Number(maxEntries) || DEFAULT_MAX_ENTRIES);
  const logPath = stateRoot ? path.join(stateRoot, QUERY_AGENT_CALL_LOG_FILE) : "";
  let pending = Promise.resolve();

  async function append(entry) {
    if (!logPath) return;
    await mkdir(stateRoot, { recursive: true });
    const log = await readQueryCallLog(logPath);
    const entries = [...log.entries, { ts: nowIso(), ...entry }].slice(-normalizedMaxEntries);
    await writeTextAtomically(logPath, `${JSON.stringify({
      version: 1,
      max_entries: normalizedMaxEntries,
      updated_at: nowIso(),
      entries
    }, null, 2)}\n`);
  }

  return {
    logPath,
    record(entry) {
      if (!logPath) return Promise.resolve();
      pending = pending.then(() => append(entry)).catch(() => {});
      return pending;
    }
  };
}
