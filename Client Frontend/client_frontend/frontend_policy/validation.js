import {
  CHAT_HISTORY_KEYS,
  MEMORY_KEYS,
  MIN_AGENT_CONTEXT_KEYS,
  MIN_AGENT_KEYS,
  MIN_AGENT_RUNTIME_KEYS,
  MODEL_CATALOG_KEYS,
  ONTOLOGY_AGENT_KEYS,
  ONTOLOGY_PROMPT_SECTION_KEYS,
  PROMPT_SECTION_KEYS,
  TOP_LEVEL_KEYS
} from "./types.js";
import { cloneFrontendPolicy } from "./defaults.js";
import { failFrontendPolicy, FrontendPolicyValidationError } from "./error.js";
import {
  assertExactKeys,
  assertObject,
  readInteger,
  readNumber,
  readRegexArray,
  readSourceOrder,
  readString,
  readStringArray
} from "./validation_readers.js";

export { FrontendPolicyValidationError } from "./error.js";

function readTopLevelPolicy(value) {
  const object = assertObject(value, "frontend_policy");
  const actualKeys = Object.keys(object);
  const unexpectedKeys = actualKeys.filter((key) => !TOP_LEVEL_KEYS.includes(key)).sort();
  const requiredKeys = TOP_LEVEL_KEYS.filter((key) => key !== "ontology_agent");
  const missingKeys = requiredKeys.filter((key) => !actualKeys.includes(key)).sort();
  if (unexpectedKeys.length || missingKeys.length) {
    failFrontendPolicy("frontend_policy", `has invalid or missing keys: [${actualKeys.sort().join(", ")}].`);
  }
  return {
    ...object,
    ontology_agent: object.ontology_agent || cloneFrontendPolicy().ontology_agent
  };
}

export function normalizeFrontendPolicy(value) {
  const source = readTopLevelPolicy(value);
  const minAgent = assertExactKeys(source.min_agent, MIN_AGENT_KEYS, "frontend_policy.min_agent");
  const minAgentContext = assertExactKeys(minAgent.context, MIN_AGENT_CONTEXT_KEYS, "frontend_policy.min_agent.context");
  const minAgentRuntime = assertExactKeys(minAgent.runtime, MIN_AGENT_RUNTIME_KEYS, "frontend_policy.min_agent.runtime");
  const minAgentPrompt = assertExactKeys(minAgent.prompt, PROMPT_SECTION_KEYS, "frontend_policy.min_agent.prompt");
  const ontologyAgent = assertExactKeys(source.ontology_agent, ONTOLOGY_AGENT_KEYS, "frontend_policy.ontology_agent");
  const ontologyAgentPrompt = assertExactKeys(ontologyAgent.prompt, ONTOLOGY_PROMPT_SECTION_KEYS, "frontend_policy.ontology_agent.prompt");
  return {
    chat_history: {
      ...(() => {
        const value = assertExactKeys(source.chat_history, CHAT_HISTORY_KEYS, "frontend_policy.chat_history");
        return {
          max_history: readInteger(value.max_history, "frontend_policy.chat_history.max_history", 1, 10_000),
          title_max_length: readInteger(value.title_max_length, "frontend_policy.chat_history.title_max_length", 3, 1_000)
        };
      })()
    },
    memory: {
      ...(() => {
        const value = assertExactKeys(source.memory, MEMORY_KEYS, "frontend_policy.memory");
        return {
          max_summary_length: readInteger(value.max_summary_length, "frontend_policy.memory.max_summary_length", 1, 10_000),
          max_topics: readInteger(value.max_topics, "frontend_policy.memory.max_topics", 1, 200),
          max_search_results: readInteger(value.max_search_results, "frontend_policy.memory.max_search_results", 1, 200),
          max_query_keys: readInteger(value.max_query_keys, "frontend_policy.memory.max_query_keys", 1, 200),
          max_search_fetch: readInteger(value.max_search_fetch, "frontend_policy.memory.max_search_fetch", 1, 1_000),
          recent_days_high: readInteger(value.recent_days_high, "frontend_policy.memory.recent_days_high", 1, 3650),
          recent_days_low: readInteger(value.recent_days_low, "frontend_policy.memory.recent_days_low", 1, 3650),
          filler_patterns: readRegexArray(value.filler_patterns, "frontend_policy.memory.filler_patterns"),
          query_stop_words: readStringArray(value.query_stop_words, "frontend_policy.memory.query_stop_words"),
          topic_stop_words: readStringArray(value.topic_stop_words, "frontend_policy.memory.topic_stop_words"),
          non_memory_answer_patterns: readRegexArray(value.non_memory_answer_patterns, "frontend_policy.memory.non_memory_answer_patterns")
        };
      })()
    },
    model_catalog: {
      ...(() => {
        const value = assertExactKeys(source.model_catalog, MODEL_CATALOG_KEYS, "frontend_policy.model_catalog");
        return {
          llm_seed_models: readStringArray(value.llm_seed_models, "frontend_policy.model_catalog.llm_seed_models"),
          embedding_seed_models: readStringArray(value.embedding_seed_models, "frontend_policy.model_catalog.embedding_seed_models"),
          llm_source_order: readSourceOrder(value.llm_source_order, "frontend_policy.model_catalog.llm_source_order"),
          embedding_source_order: readSourceOrder(value.embedding_source_order, "frontend_policy.model_catalog.embedding_source_order")
        };
      })()
    },
    min_agent: {
      context: {
        history_context_ratio: readNumber(minAgentContext.history_context_ratio, "frontend_policy.min_agent.context.history_context_ratio", 0.01, 1),
        history_token_cap: readInteger(minAgentContext.history_token_cap, "frontend_policy.min_agent.context.history_token_cap", 1, 10_000_000),
        system_overhead_tokens: readInteger(minAgentContext.system_overhead_tokens, "frontend_policy.min_agent.context.system_overhead_tokens", 0, 10_000_000),
        average_turn_tokens: readInteger(minAgentContext.average_turn_tokens, "frontend_policy.min_agent.context.average_turn_tokens", 1, 10_000_000)
      },
      runtime: {
        max_tool_rounds: readInteger(minAgentRuntime.max_tool_rounds, "frontend_policy.min_agent.runtime.max_tool_rounds", 1, 256),
        max_sql_rows: readInteger(minAgentRuntime.max_sql_rows, "frontend_policy.min_agent.runtime.max_sql_rows", 1, 10_000),
        max_text_length: readInteger(minAgentRuntime.max_text_length, "frontend_policy.min_agent.runtime.max_text_length", 1, 500_000),
        max_field_count: readInteger(minAgentRuntime.max_field_count, "frontend_policy.min_agent.runtime.max_field_count", 1, 10_000),
        max_evidence_count: readInteger(minAgentRuntime.max_evidence_count, "frontend_policy.min_agent.runtime.max_evidence_count", 1, 10_000),
        max_row_count: readInteger(minAgentRuntime.max_row_count, "frontend_policy.min_agent.runtime.max_row_count", 1, 10_000),
        max_workbench_output: readInteger(minAgentRuntime.max_workbench_output, "frontend_policy.min_agent.runtime.max_workbench_output", 256, 1_000_000),
        default_workbench_timeout_ms: readInteger(minAgentRuntime.default_workbench_timeout_ms, "frontend_policy.min_agent.runtime.default_workbench_timeout_ms", 1_000, 30_000)
      },
      prompt: Object.fromEntries(PROMPT_SECTION_KEYS.map((key) => [key, readString(minAgentPrompt[key], `frontend_policy.min_agent.prompt.${key}`)]))
    },
    ontology_agent: {
      prompt: Object.fromEntries(ONTOLOGY_PROMPT_SECTION_KEYS.map((key) => [key, readString(ontologyAgentPrompt[key], `frontend_policy.ontology_agent.prompt.${key}`)]))
    }
  };
}

export function parseFrontendPolicyText(rawText) {
  try {
    return normalizeFrontendPolicy(JSON.parse(String(rawText || "")));
  } catch (error) {
    if (error instanceof FrontendPolicyValidationError) {
      throw error;
    }
    throw new FrontendPolicyValidationError(
      `frontend_policy.json is not valid JSON: ${error instanceof Error ? error.message : error}`,
      "invalid_json"
    );
  }
}

export function compileRegexDescriptors(descriptors = []) {
  return descriptors.map((descriptor) => new RegExp(descriptor.pattern, descriptor.flags));
}
