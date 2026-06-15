import type { FrontendPolicy, FrontendPolicySourceOrderValue, RegexDescriptor } from "../../types/frontend_policy.ts";
import { ONTOLOGY_PROMPT_FIELD_ORDER, PROMPT_FIELD_ORDER, SOURCE_ORDER_VALUES } from "./constants.ts";
import { collectRegexDraftRows } from "./regex_editor.ts";
import type { FrontendPolicyDomRefs, RegexListDomRefs } from "./types.ts";

export class FrontendPolicyInputError extends Error {
  field = "frontend_policy";
  policyPath?: string;

  constructor(message: string, policyPath?: string) {
    super(message);
    this.name = "FrontendPolicyInputError";
    this.policyPath = policyPath;
  }
}

function fail(path: string, detail: string): never {
  throw new FrontendPolicyInputError(`${path} ${detail}`, path);
}

function readInteger(input: HTMLInputElement | null, path: string, min: number, max: number): number {
  const parsed = Number(input?.value || "");
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    fail(path, `must be an integer between ${min} and ${max}.`);
  }
  return parsed;
}

function readNumber(input: HTMLInputElement | null, path: string, min: number, max: number): number {
  const parsed = Number(input?.value || "");
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) {
    fail(path, `must be a number between ${min} and ${max}.`);
  }
  return parsed;
}

function readList(input: HTMLTextAreaElement | null): string[] {
  return Array.from(new Set(String(input?.value || "").split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean)));
}

function readSourceOrder(inputs: HTMLSelectElement[], path: string): FrontendPolicySourceOrderValue[] {
  const values = inputs.map((input) => String(input.value || "").trim()).filter(Boolean);
  if (values.length !== SOURCE_ORDER_VALUES.length || new Set(values).size !== values.length) {
    fail(path, "must contain each source exactly once.");
  }
  if (values.some((value) => !SOURCE_ORDER_VALUES.includes(value as FrontendPolicySourceOrderValue))) {
    fail(path, "contains invalid source values.");
  }
  return values as FrontendPolicySourceOrderValue[];
}

function readRegexList(list: RegexListDomRefs, path: string): RegexDescriptor[] {
  return collectRegexDraftRows(list).flatMap((descriptor, index) => {
    const entryPath = `${path}[${index}]`;
    if (!descriptor.pattern.trim() && !descriptor.flags) {
      return [];
    }
    if (!descriptor.pattern.trim()) {
      fail(`${entryPath}.pattern`, "must not be empty.");
    }
    if (!/^(?:[dgimsuvy]{0,8})$/.test(descriptor.flags) || new Set(descriptor.flags).size !== descriptor.flags.length) {
      fail(`${entryPath}.flags`, "contains invalid regex flags.");
    }
    try {
      new RegExp(descriptor.pattern, descriptor.flags);
    } catch (error) {
      fail(entryPath, `contains an invalid regex pattern: ${error instanceof Error ? error.message : error}`);
    }
    return [descriptor];
  });
}

export function collectFrontendPolicy(dom: FrontendPolicyDomRefs): FrontendPolicy {
  return {
    chat_history: {
      max_history: readInteger(dom.chatHistory.maxHistoryInput, "frontend_policy.chat_history.max_history", 1, 10_000),
      title_max_length: readInteger(dom.chatHistory.titleMaxLengthInput, "frontend_policy.chat_history.title_max_length", 3, 1_000)
    },
    memory: {
      max_summary_length: readInteger(dom.memory.maxSummaryLengthInput, "frontend_policy.memory.max_summary_length", 1, 10_000),
      max_topics: readInteger(dom.memory.maxTopicsInput, "frontend_policy.memory.max_topics", 1, 200),
      max_search_results: readInteger(dom.memory.maxSearchResultsInput, "frontend_policy.memory.max_search_results", 1, 200),
      max_query_keys: readInteger(dom.memory.maxQueryKeysInput, "frontend_policy.memory.max_query_keys", 1, 200),
      max_search_fetch: readInteger(dom.memory.maxSearchFetchInput, "frontend_policy.memory.max_search_fetch", 1, 1_000),
      recent_days_high: readInteger(dom.memory.recentDaysHighInput, "frontend_policy.memory.recent_days_high", 1, 3650),
      recent_days_low: readInteger(dom.memory.recentDaysLowInput, "frontend_policy.memory.recent_days_low", 1, 3650),
      filler_patterns: readRegexList(dom.memory.fillerPatterns, "frontend_policy.memory.filler_patterns"),
      query_stop_words: readList(dom.memory.queryStopWordsInput),
      topic_stop_words: readList(dom.memory.topicStopWordsInput),
      non_memory_answer_patterns: readRegexList(dom.memory.nonMemoryAnswerPatterns, "frontend_policy.memory.non_memory_answer_patterns")
    },
    model_catalog: {
      llm_seed_models: readList(dom.modelCatalog.llmSeedModelsInput),
      embedding_seed_models: readList(dom.modelCatalog.embeddingSeedModelsInput),
      llm_source_order: readSourceOrder(dom.modelCatalog.llmSourceOrderInputs, "frontend_policy.model_catalog.llm_source_order"),
      embedding_source_order: readSourceOrder(dom.modelCatalog.embeddingSourceOrderInputs, "frontend_policy.model_catalog.embedding_source_order")
    },
    min_agent: {
      context: {
        history_context_ratio: readNumber(dom.minAgentContext.historyContextRatioInput, "frontend_policy.min_agent.context.history_context_ratio", 0.01, 1),
        history_token_cap: readInteger(dom.minAgentContext.historyTokenCapInput, "frontend_policy.min_agent.context.history_token_cap", 1, 10_000_000),
        system_overhead_tokens: readInteger(dom.minAgentContext.systemOverheadTokensInput, "frontend_policy.min_agent.context.system_overhead_tokens", 0, 10_000_000),
        average_turn_tokens: readInteger(dom.minAgentContext.averageTurnTokensInput, "frontend_policy.min_agent.context.average_turn_tokens", 1, 10_000_000)
      },
      runtime: {
        max_tool_rounds: readInteger(dom.minAgentRuntime.maxToolRoundsInput, "frontend_policy.min_agent.runtime.max_tool_rounds", 1, 256),
        max_sql_rows: readInteger(dom.minAgentRuntime.maxSqlRowsInput, "frontend_policy.min_agent.runtime.max_sql_rows", 1, 10_000),
        max_text_length: readInteger(dom.minAgentRuntime.maxTextLengthInput, "frontend_policy.min_agent.runtime.max_text_length", 1, 500_000),
        max_field_count: readInteger(dom.minAgentRuntime.maxFieldCountInput, "frontend_policy.min_agent.runtime.max_field_count", 1, 10_000),
        max_evidence_count: readInteger(dom.minAgentRuntime.maxEvidenceCountInput, "frontend_policy.min_agent.runtime.max_evidence_count", 1, 10_000),
        max_row_count: readInteger(dom.minAgentRuntime.maxRowCountInput, "frontend_policy.min_agent.runtime.max_row_count", 1, 10_000),
        max_workbench_output: readInteger(dom.minAgentRuntime.maxWorkbenchOutputInput, "frontend_policy.min_agent.runtime.max_workbench_output", 256, 1_000_000),
        default_workbench_timeout_ms: readInteger(dom.minAgentRuntime.defaultWorkbenchTimeoutInput, "frontend_policy.min_agent.runtime.default_workbench_timeout_ms", 1_000, 30_000)
      },
      prompt: Object.fromEntries(
        PROMPT_FIELD_ORDER.map(([key]) => [key, String(dom.minAgentPrompt[key]?.value || "")])
      ) as FrontendPolicy["min_agent"]["prompt"]
    },
    ontology_agent: {
      prompt: Object.fromEntries(
        ONTOLOGY_PROMPT_FIELD_ORDER.map(([key]) => [key, String(dom.ontologyAgentPrompt[key]?.value || "")])
      ) as FrontendPolicy["ontology_agent"]["prompt"]
    }
  };
}
