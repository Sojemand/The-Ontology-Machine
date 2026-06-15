import path from "node:path";

import { createChatCompletion, embedTexts } from "../provider.js";
import { createEstimatedTokenUsageTracker } from "../token_usage.js";
import { ONTOLOGY_MAX_TOOL_ROUNDS, ONTOLOGY_TOOL_DEFINITIONS } from "./types.js";
import { createOntologyRepository } from "./repository.js";
import {
  buildOntologySystemPrompt,
  extractAssistantText,
  trimOntologyHistoryForContext
} from "./policy.js";
import { runBasicRelationMiningWithKernel } from "./kernel_basic_relation_mining.js";
import { buildRepairInstruction, isRepairableSqlBatchFailure, MAX_SQL_REPAIR_ROUNDS } from "./workflow_repair.js";
import { compactSqlBatchForHistory } from "./workflow_context_compaction.js";
import { executeOntologyToolCall } from "./workflow_tools.js";
import { createOntologyCallLogger } from "./call_logger.js";
import { createOntologyTurnId, logTurnError, logTurnFinal, logTurnStart, runLoggedLlmCall, runLoggedToolCall } from "./workflow_logging.js";

export function createOntologyAgent({
  dbPath,
  dataDir = path.dirname(dbPath),
  rootDir = path.dirname(dataDir),
  pipelineRoot = rootDir,
  stateRoot = "",
  soulContext = "",
  frontendPolicy = null,
  getFrontendPolicy,
  runtimeConfig,
  getRuntimeConfig,
  createChatCompletionFn = createChatCompletion,
  embedTextsFn = embedTexts,
  validatePatchFn,
  runBasicRelationMiningFn = runBasicRelationMiningWithKernel
}) {
  const repository = createOntologyRepository({
    dbPath,
    dataDir,
    pipelineRoot,
    getRuntimeConfig: () => (typeof getRuntimeConfig === "function" ? getRuntimeConfig() : runtimeConfig),
    embedTextsFn,
    validatePatchFn
  });
  const corpusDocCount = repository.countDocuments();
  const readRuntimeConfig = () => (typeof getRuntimeConfig === "function" ? getRuntimeConfig() : runtimeConfig);
  const readFrontendPolicy = () => (typeof getFrontendPolicy === "function" ? getFrontendPolicy() : frontendPolicy);
  const trimAssistantHistory = (history) => trimOntologyHistoryForContext(history, readRuntimeConfig()?.context_limit, readFrontendPolicy());
  const callLogger = createOntologyCallLogger({ stateRoot });

  async function chat({ message, history = [] }) {
    const userMessage = String(message || "").trim();
    const sources = new Map();
    const activeRuntimeConfig = readRuntimeConfig();
    const activeFrontendPolicy = readFrontendPolicy();
    const turnId = createOntologyTurnId();
    const tokenUsage = createEstimatedTokenUsageTracker();
    const messages = [
      {
        role: "system",
        content: buildOntologySystemPrompt({
          schemaSummary: repository.schemaSummary,
          corpusDocCount,
          soulContext,
          frontendPolicy: activeFrontendPolicy
        })
      },
      ...trimOntologyHistoryForContext(history, activeRuntimeConfig?.context_limit, activeFrontendPolicy),
      { role: "user", content: userMessage }
    ];
    const repairState = {
      active: false,
      attempts: 0,
      lastResult: null,
      nudges: 0
    };
    await logTurnStart(callLogger, { turnId, userMessage, history, corpusDocCount, runtimeConfig: activeRuntimeConfig });

    for (let round = 0; round < ONTOLOGY_MAX_TOOL_ROUNDS; round += 1) {
      tokenUsage.recordInput(messages);
      const assistantMessage = await runLoggedLlmCall(callLogger, {
        turnId,
        round,
        runtimeConfig: activeRuntimeConfig,
        messages,
        tools: ONTOLOGY_TOOL_DEFINITIONS,
        createChatCompletionFn
      });
      if (!assistantMessage) {
        await logTurnError(callLogger, { turnId, round, message: "Empty model response." });
        throw new Error("Empty model response.");
      }
      tokenUsage.recordAssistantMessage(assistantMessage);
      if (!assistantMessage.tool_calls?.length) {
        if (
          repairState.active
          && repairState.attempts > 0
          && repairState.attempts <= MAX_SQL_REPAIR_ROUNDS
          && repairState.nudges < MAX_SQL_REPAIR_ROUNDS
        ) {
          repairState.nudges += 1;
          messages.push({ role: "assistant", content: assistantMessage.content || "" });
          messages.push({ role: "user", content: buildRepairInstruction(repairState.lastResult, repairState.attempts, { nudge: true }) });
          continue;
        }
        const answer = extractAssistantText(assistantMessage) || "I could not formulate a reliable ontology answer.";
        await logTurnFinal(callLogger, { turnId, round, answer, sourceCount: sources.size });
        return {
          answer,
          sources: Array.from(sources.values()),
          history: trimAssistantHistory([...history, { role: "user", content: userMessage }, { role: "assistant", content: answer }]),
          mode: "analytic",
          exactness: sources.size ? "evidence_grounded" : "insufficient_evidence",
          metrics: { scope_documents: corpusDocCount, matched_documents: sources.size, matched_occurrences: 0, aggregated_values: null },
          ambiguities: [],
          method: "ontology_agent",
          token_usage: tokenUsage.snapshot()
        };
      }
      const assistantHistoryMessage = {
        role: "assistant",
        content: assistantMessage.content || "",
        tool_calls: assistantMessage.tool_calls.map((toolCall) => ({ ...toolCall, function: { ...toolCall.function } }))
      };
      messages.push(assistantHistoryMessage);
      for (const [toolIndex, toolCall] of assistantMessage.tool_calls.entries()) {
        const { result, resultDocIds } = await runLoggedToolCall(callLogger, {
          turnId,
          round,
          toolIndex,
          toolCall,
          execute: () => executeOntologyToolCall(toolCall, {
            repository,
            readFrontendPolicy,
            readRuntimeConfig,
            embedTextsFn,
            runBasicRelationMiningFn,
            pipelineRoot,
            dbPath,
            stateRoot
          })
        });
        if (toolCall?.function?.name === "sql_batch_execute" && result?.ok === true) {
          repairState.active = false;
          repairState.attempts = 0;
          repairState.lastResult = null;
          repairState.nudges = 0;
        }
        for (const docId of resultDocIds) {
          const source = repository.buildSource(docId);
          const key = source?.source_key || source?.id || docId;
          if (source && !sources.has(key)) sources.set(key, source);
        }
        const historyPatch = compactSqlBatchForHistory(toolCall, result);
        assistantHistoryMessage.tool_calls[toolIndex] = historyPatch.toolCall;
        messages.push({ role: "tool", tool_call_id: toolCall.id, content: historyPatch.toolResultContent });
        if (isRepairableSqlBatchFailure(toolCall, result)) {
          repairState.active = true;
          repairState.lastResult = result;
          repairState.attempts += 1;
          repairState.nudges = 0;
          if (repairState.attempts <= MAX_SQL_REPAIR_ROUNDS) {
            messages.push({ role: "user", content: buildRepairInstruction(result, repairState.attempts) });
          }
        }
      }
    }
    await logTurnError(callLogger, { turnId, message: "Too many ontology tool rounds without a final answer.", maxRounds: ONTOLOGY_MAX_TOOL_ROUNDS });
    throw new Error("Too many ontology tool rounds without a final answer.");
  }

  return {
    schemaSummary: repository.schemaSummary,
    chat,
    countDocuments() {
      return repository.countDocuments();
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
