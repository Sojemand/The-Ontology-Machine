import path from "node:path";

import { resolveMinAgentRuntimePolicy } from "../frontend_policy.js";
import { createChatCompletion, embedTexts } from "../provider.js";
import { createEstimatedTokenUsageTracker } from "../token_usage.js";
import { buildWorkbenchErrorResult, runWorkbench } from "./adapter.js";
import { createQueryCallLogger } from "./call_logger.js";
import { buildSystemPrompt, extractAssistantText, trimHistoryForContext } from "./policy.js";
import { buildSqlErrorResult } from "./query_repository.js";
import { createMinimalRepository } from "./repository.js";
import { extractDocIdsFromRows } from "./source_domain.js";
import { MAX_TOOL_ROUNDS, TOOL_DEFINITIONS } from "./types.js";
import {
  createQueryTurnId,
  logToolCallEnd,
  logToolCallError,
  logToolCallStart,
  logTurnError,
  logTurnFinal,
  logTurnStart,
  runLoggedLlmCall
} from "./workflow_logging.js";

function parseToolArguments(toolCall) {
  try {
    return JSON.parse(toolCall?.function?.arguments || "{}");
  } catch {
    return null;
  }
}

const DOCUMENT_SOURCE_TOOL_NAMES = new Set([
  "get_document",
  "get_document_summary",
  "get_document_ontology_evidence",
  "get_document_rows",
  "get_document_provenance",
  "get_document_full",
  "get_provenance"
]);

export function createMinimalAgent({
  dbPath,
  dataDir = path.dirname(dbPath),
  rootDir = path.dirname(dataDir),
  configDir = rootDir,
  stateRoot = "",
  soulContext = "",
  frontendPolicy = null,
  getFrontendPolicy,
  runtimeConfig,
  getRuntimeConfig,
  createChatCompletionFn = createChatCompletion,
  embedTextsFn = embedTexts,
  runWorkbenchFn = runWorkbench
}) {
  const repository = createMinimalRepository({ dbPath, dataDir });
  const corpusDocCount = repository.countDocuments();
  const readRuntimeConfig = () => (typeof getRuntimeConfig === "function" ? getRuntimeConfig() : runtimeConfig);
  const readFrontendPolicy = () => (typeof getFrontendPolicy === "function" ? getFrontendPolicy() : frontendPolicy);
  const trimAssistantHistory = (history) => trimHistoryForContext(history, readRuntimeConfig()?.context_limit, readFrontendPolicy());
  const callLogger = createQueryCallLogger({ stateRoot });

  async function executeToolCall(toolCall) {
    const args = parseToolArguments(toolCall);
    if (!args) return { error: "Tool arguments could not be read." };
    const runtimePolicy = resolveMinAgentRuntimePolicy(readFrontendPolicy());
    const toolHandlers = {
      async sql_query() {
        try {
          return repository.sqlQuery(args.query, runtimePolicy);
        } catch (error) {
          return buildSqlErrorResult(error, args.query, repository.schemaSummary);
        }
      },
      async get_document() {
        try {
          return repository.getDocument(args.doc_id, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_document failed.", doc_id: args.doc_id };
        }
      },
      async get_document_summary() {
        try {
          return repository.getDocumentSummary(args.doc_id, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_document_summary failed.", doc_id: args.doc_id };
        }
      },
      async get_document_ontology_evidence() {
        try {
          return repository.getDocumentOntologyEvidence(args.doc_id, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_document_ontology_evidence failed.", doc_id: args.doc_id };
        }
      },
      async get_document_rows() {
        try {
          return repository.getDocumentRows(args.doc_id, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_document_rows failed.", doc_id: args.doc_id };
        }
      },
      async get_document_provenance() {
        try {
          return repository.getDocumentProvenance(args.doc_id, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_document_provenance failed.", doc_id: args.doc_id };
        }
      },
      async get_document_full() {
        try {
          return repository.getDocumentFull(args.doc_id, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_document_full failed.", doc_id: args.doc_id };
        }
      },
      async get_provenance() {
        try {
          return repository.getProvenance(args.doc_id, args.target, args.target_kind, runtimePolicy);
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : "get_provenance failed.", doc_id: args.doc_id, target: args.target };
        }
      },
      async semantic_search() {
        const activeRuntimeConfig = readRuntimeConfig();
        const indexState = repository.semanticIndexState();
        if (!indexState.available) {
          return {
            ...indexState,
            fallback: repository.keywordSearch(args.text, args.limit)
          };
        }
        try {
          const [queryVector] = await embedTextsFn(activeRuntimeConfig, [args.text]);
          return repository.semanticSearch(Float32Array.from(queryVector), args.limit);
        } catch (error) {
          return {
            available: false,
            error: error instanceof Error ? error.message : "semantic_search failed.",
            results: [],
            fallback: repository.keywordSearch(args.text, args.limit)
          };
        }
      },
      async database_coverage_snapshot() {
        return repository.databaseCoverageSnapshot(args);
      },
      async list_source_documents() {
        return repository.listSourceDocuments(args);
      },
      async get_source_document() {
        return repository.getSourceDocument(args);
      },
      async list_ontology_lenses() {
        return repository.listOntologyLenses(args);
      },
      async get_ontology_lens() {
        return repository.getOntologyLens(args);
      },
      async workbench() {
        try {
          const result = await runWorkbenchFn({
            runtime: args.runtime,
            code: args.code,
            timeoutMs: args.timeout_ms,
            rootDir,
            dataDir,
            configDir,
            runtimePolicy,
            env: { MIN_AGENT_ROOT_DIR: rootDir, MIN_AGENT_DB_PATH: dbPath, MIN_AGENT_DATA_DIR: dataDir }
          });
          return { ...result, sources: repository.extractSourcesFromWorkbenchOutput(result.stdout, result.stderr) };
        } catch (error) {
          return buildWorkbenchErrorResult(error, args.runtime, args.code);
        }
      }
    };
    const handler = toolHandlers[toolCall?.function?.name];
    return handler ? await handler() : { error: `Unknown tool: ${toolCall?.function?.name}` };
  }

  async function chat({ message, history = [] }) {
    const userMessage = String(message || "").trim();
    const sources = new Map();
    const activeRuntimeConfig = readRuntimeConfig();
    const activeFrontendPolicy = readFrontendPolicy();
    const turnId = createQueryTurnId();
    const runtimePolicy = resolveMinAgentRuntimePolicy(activeFrontendPolicy);
    const tokenUsage = createEstimatedTokenUsageTracker();
    const messages = [
      { role: "system", content: buildSystemPrompt(repository.schemaSummary, corpusDocCount, soulContext, activeFrontendPolicy) },
      ...trimHistoryForContext(history, activeRuntimeConfig?.context_limit, activeFrontendPolicy),
      { role: "user", content: userMessage }
    ];
    await logTurnStart(callLogger, { turnId, userMessage, history, corpusDocCount, runtimeConfig: activeRuntimeConfig });
    for (let round = 0; round < runtimePolicy.max_tool_rounds; round += 1) {
      tokenUsage.recordInput(messages);
      const assistantMessage = await runLoggedLlmCall(callLogger, {
        turnId,
        round,
        runtimeConfig: activeRuntimeConfig,
        messages,
        tools: TOOL_DEFINITIONS,
        createChatCompletionFn
      });
      if (!assistantMessage) {
        await logTurnError(callLogger, { turnId, round, message: "Empty model response." });
        throw new Error("Empty model response.");
      }
      tokenUsage.recordAssistantMessage(assistantMessage);
      if (!assistantMessage.tool_calls?.length) {
        const answer = extractAssistantText(assistantMessage) || "I could not formulate a reliable answer.";
        const tokenUsageSnapshot = tokenUsage.snapshot();
        await logTurnFinal(callLogger, { turnId, round, answer, sourceCount: sources.size, tokenUsage: tokenUsageSnapshot });
        return {
          answer,
          sources: Array.from(sources.values()),
          history: trimAssistantHistory([...history, { role: "user", content: userMessage }, { role: "assistant", content: answer }]),
          mode: "lookup",
          exactness: sources.size ? "evidence_grounded" : "insufficient_evidence",
          metrics: { scope_documents: 0, matched_documents: sources.size, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "minimal_agent",
          token_usage: tokenUsageSnapshot
        };
      }
      messages.push({ role: "assistant", content: assistantMessage.content || "", tool_calls: assistantMessage.tool_calls });
      for (const [toolIndex, toolCall] of assistantMessage.tool_calls.entries()) {
        const startedAt = Date.now();
        await logToolCallStart(callLogger, { turnId, round, toolIndex, toolCall });
        let result;
        let docIds;
        try {
          result = await executeToolCall(toolCall);
          docIds = DOCUMENT_SOURCE_TOOL_NAMES.has(toolCall.function.name)
            ? result?.source?.id ? [result.source.id] : []
            : [
                ...extractDocIdsFromRows(result?.rows || result?.results || []),
                ...extractDocIdsFromRows(result?.fallback?.rows || result?.fallback?.results || []),
                ...((Array.isArray(result?.sources) ? result.sources : []).map((source) => source?.id).filter(Boolean))
              ];
          await logToolCallEnd(callLogger, { turnId, round, toolIndex, toolCall, startedAt, result, resultDocIds: docIds });
        } catch (error) {
          await logToolCallError(callLogger, { turnId, round, toolIndex, toolCall, startedAt, error });
          throw error;
        }
        for (const docId of docIds) {
          const source = repository.buildSource(docId);
          const key = source?.source_key || source?.id || docId;
          if (source && !sources.has(key)) sources.set(key, source);
        }
        messages.push({ role: "tool", tool_call_id: toolCall.id, content: JSON.stringify(result) });
      }
    }
    await logTurnError(callLogger, { turnId, message: "Too many tool rounds without a final answer.", maxRounds: runtimePolicy.max_tool_rounds });
    throw new Error("Too many tool rounds without a final answer.");
  }

  return {
    schemaSummary: repository.schemaSummary,
    chat,
    countDocuments() {
      return repository.countDocuments();
    },
    databaseStatus() {
      return repository.databaseStructureStatus();
    },
    resolveImage(docId, page) {
      return repository.resolveImage(docId, page);
    },
    resolveSource(docId) {
      return repository.buildSource(docId);
    },
    resolveSourcesFromText(text) {
      return repository.extractSourcesFromText(text);
    },
    close() {
      repository.close();
    }
  };
}
