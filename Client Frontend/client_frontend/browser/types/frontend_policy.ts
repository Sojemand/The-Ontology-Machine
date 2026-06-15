export type FrontendPolicySourceOrderValue = "live" | "cache" | "seed" | "fallback";

export interface RegexDescriptor {
  pattern: string;
  flags: string;
}

export interface ChatHistoryPolicy {
  max_history: number;
  title_max_length: number;
}

export interface MemoryPolicy {
  max_summary_length: number;
  max_topics: number;
  max_search_results: number;
  max_query_keys: number;
  max_search_fetch: number;
  recent_days_high: number;
  recent_days_low: number;
  filler_patterns: RegexDescriptor[];
  query_stop_words: string[];
  topic_stop_words: string[];
  non_memory_answer_patterns: RegexDescriptor[];
}

export interface ModelCatalogPolicy {
  llm_seed_models: string[];
  embedding_seed_models: string[];
  llm_source_order: FrontendPolicySourceOrderValue[];
  embedding_source_order: FrontendPolicySourceOrderValue[];
}

export interface MinAgentContextPolicy {
  history_context_ratio: number;
  history_token_cap: number;
  system_overhead_tokens: number;
  average_turn_tokens: number;
}

export interface MinAgentRuntimePolicy {
  max_tool_rounds: number;
  max_sql_rows: number;
  max_text_length: number;
  max_field_count: number;
  max_evidence_count: number;
  max_row_count: number;
  max_workbench_output: number;
  default_workbench_timeout_ms: number;
}

export interface MinAgentPromptPolicy {
  identity: string;
  analysis: string;
  evidence: string;
  data_layers: string;
  tool_routing: string;
  workbench: string;
  answer_rules: string;
}

export interface OntologyAgentPromptPolicy {
  identity: string;
  mission: string;
  intent_architecture: string;
  analysis: string;
  working_method: string;
  data_layers: string;
  ontology_layers: string;
  tool_routing: string;
  lens_lifecycle: string;
  foreign_key_order: string;
  insert_contract: string;
  write_discipline: string;
  preflight_repair: string;
  write_policy: string;
  evidence_policy: string;
  answer_rules: string;
}

export interface FrontendPolicy {
  chat_history: ChatHistoryPolicy;
  memory: MemoryPolicy;
  model_catalog: ModelCatalogPolicy;
  min_agent: {
    context: MinAgentContextPolicy;
    runtime: MinAgentRuntimePolicy;
    prompt: MinAgentPromptPolicy;
  };
  ontology_agent: {
    prompt: OntologyAgentPromptPolicy;
  };
}

export interface FrontendPolicyDiagnostics {
  status: "invalid_json" | "invalid_policy";
  message: string;
  raw_text: string;
  policy_path?: string;
}
