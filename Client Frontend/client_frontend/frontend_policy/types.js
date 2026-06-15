export const FRONTEND_POLICY_FILE_NAME = "frontend_policy.json";

export const SOURCE_ORDER_VALUES = ["live", "cache", "seed", "fallback"];
export const PROMPT_SECTION_KEYS = ["identity", "analysis", "evidence", "data_layers", "tool_routing", "workbench", "answer_rules"];
export const ONTOLOGY_PROMPT_SECTION_KEYS = [
  "identity",
  "mission",
  "intent_architecture",
  "analysis",
  "working_method",
  "data_layers",
  "ontology_layers",
  "tool_routing",
  "lens_lifecycle",
  "foreign_key_order",
  "insert_contract",
  "write_discipline",
  "preflight_repair",
  "write_policy",
  "evidence_policy",
  "answer_rules"
];

export const TOP_LEVEL_KEYS = ["chat_history", "memory", "model_catalog", "min_agent", "ontology_agent"];
export const CHAT_HISTORY_KEYS = ["max_history", "title_max_length"];
export const MEMORY_KEYS = [
  "max_summary_length",
  "max_topics",
  "max_search_results",
  "max_query_keys",
  "max_search_fetch",
  "recent_days_high",
  "recent_days_low",
  "filler_patterns",
  "query_stop_words",
  "topic_stop_words",
  "non_memory_answer_patterns"
];
export const MODEL_CATALOG_KEYS = ["llm_seed_models", "embedding_seed_models", "llm_source_order", "embedding_source_order"];
export const MIN_AGENT_KEYS = ["context", "runtime", "prompt"];
export const ONTOLOGY_AGENT_KEYS = ["prompt"];
export const MIN_AGENT_CONTEXT_KEYS = ["history_context_ratio", "history_token_cap", "system_overhead_tokens", "average_turn_tokens"];
export const MIN_AGENT_RUNTIME_KEYS = [
  "max_tool_rounds",
  "max_sql_rows",
  "max_text_length",
  "max_field_count",
  "max_evidence_count",
  "max_row_count",
  "max_workbench_output",
  "default_workbench_timeout_ms"
];
export const REGEX_DESCRIPTOR_KEYS = ["pattern", "flags"];
