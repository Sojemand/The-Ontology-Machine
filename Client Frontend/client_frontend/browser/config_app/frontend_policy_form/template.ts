import { ONTOLOGY_PROMPT_FIELD_ORDER, PROMPT_FIELD_ORDER, SOURCE_ORDER_LABELS, SOURCE_ORDER_VALUES } from "./constants.ts";

function numberField(id: string, path: string, label: string, min: number, max: number, step = 1): string {
  return `<label><span>${label}</span><input id="${id}" data-policy-path="${path}" type="number" min="${min}" max="${max}" step="${step}" /></label>`;
}

function scrollField(id: string, path: string, label: string, rows: number, helper: string, extraClass = ""): string {
  const className = ["policy-scroll-input", extraClass].filter(Boolean).join(" ");
  return [
    "<label>",
    `<span>${label}</span>`,
    `<textarea id="${id}" class="${className}" data-policy-path="${path}" rows="${rows}" spellcheck="false"></textarea>`,
    `<small class="muted">${helper}</small>`,
    "</label>"
  ].join("");
}

function sourceOrderBlock(prefix: string, path: string, heading: string): string {
  return [
    `<div class="policy-subgroup" data-policy-path-prefix="${path}">`,
    `<h4>${heading}</h4>`,
    '<div class="policy-select-grid">',
    ...SOURCE_ORDER_LABELS.map((label, index) => [
      "<label>",
      `<span>${label}</span>`,
      `<select id="${prefix}-${index}" data-policy-path-prefix="${path}">`,
      ...SOURCE_ORDER_VALUES.map((value) => `<option value="${value}">${value}</option>`),
      "</select>",
      "</label>"
    ].join("")),
    "</div>",
    "</div>"
  ].join("");
}

function regexBlock(listKey: string, path: string, heading: string, helper: string): string {
  return [
    `<div class="policy-subgroup policy-regex-group" data-policy-path-prefix="${path}">`,
    `<div class="section-head"><h4>${heading}</h4><button type="button" class="ghost-button" data-add-regex="${listKey}">Add Regex</button></div>`,
    `<small class="muted">${helper}</small>`,
    `<div id="fp-${listKey}-rows" class="policy-regex-rows" data-regex-rows="${listKey}"></div>`,
    "</div>"
  ].join("");
}

function group(title: string, path: string, body: string, helper = ""): string {
  return [
    `<section class="policy-group" data-policy-path-prefix="${path}">`,
    `<h3>${title}</h3>`,
    helper ? `<p class="muted">${helper}</p>` : "",
    body,
    "</section>"
  ].join("");
}

function promptFields(fieldOrder: readonly (readonly [string, string])[], pathPrefix: string, idPrefix: string): string {
  return `<div class="policy-prompt-grid">${fieldOrder.map(([key, label]) => scrollField(`${idPrefix}-${key}`, `${pathPrefix}.${key}`, label, 5, "Multiline, scrollable.", "policy-prompt-input")).join("")}</div>`;
}

export function buildPromptPolicyFormMarkup(): string {
  return [
    '<div class="policy-prompt-tabs" role="tablist" aria-label="Agent prompt">',
    '<button type="button" class="policy-prompt-tab" data-policy-prompt-tab="query" aria-selected="true">Query Prompt</button>',
    '<button type="button" class="policy-prompt-tab" data-policy-prompt-tab="ontology" aria-selected="false">Ontology Prompt</button>',
    "</div>",
    '<div class="policy-prompt-panel" data-policy-prompt-panel="query">',
    group(
      "Query Agent Prompt",
      "frontend_policy.min_agent.prompt",
      promptFields(PROMPT_FIELD_ORDER, "frontend_policy.min_agent.prompt", "fp-prompt")
    ),
    "</div>",
    '<div class="policy-prompt-panel" data-policy-prompt-panel="ontology" hidden>',
    group(
      "Ontology Agent Prompt",
      "frontend_policy.ontology_agent.prompt",
      promptFields(ONTOLOGY_PROMPT_FIELD_ORDER, "frontend_policy.ontology_agent.prompt", "fp-ontology-prompt")
    ),
    "</div>"
  ].join("");
}

export function buildFrontendPolicyFormMarkup(): string {
  return [
    group(
      "Chat History",
      "frontend_policy.chat_history",
      `<div class="grid-two">${numberField("fp-chat-max-history", "frontend_policy.chat_history.max_history", "Max. Histories", 1, 10000)}${numberField("fp-chat-title-max-length", "frontend_policy.chat_history.title_max_length", "Title Length", 3, 1000)}</div>`
    ),
    group(
      "Memory",
      "frontend_policy.memory",
      [
        `<div class="grid-two">${numberField("fp-memory-max-summary-length", "frontend_policy.memory.max_summary_length", "Summary Length", 1, 10000)}${numberField("fp-memory-max-topics", "frontend_policy.memory.max_topics", "Max. Topics", 1, 200)}${numberField("fp-memory-max-search-results", "frontend_policy.memory.max_search_results", "Max. Search Results", 1, 200)}${numberField("fp-memory-max-query-keys", "frontend_policy.memory.max_query_keys", "Max. Query Keys", 1, 200)}${numberField("fp-memory-max-search-fetch", "frontend_policy.memory.max_search_fetch", "Max. Fetch", 1, 1000)}${numberField("fp-memory-recent-days-high", "frontend_policy.memory.recent_days_high", "Recent Days High", 1, 3650)}${numberField("fp-memory-recent-days-low", "frontend_policy.memory.recent_days_low", "Recent Days Low", 1, 3650)}</div>`,
        `<div class="grid-two">${scrollField("fp-memory-query-stop-words", "frontend_policy.memory.query_stop_words", "Query Stopwords", 7, "One entry per line.", "policy-list-input")}${scrollField("fp-memory-topic-stop-words", "frontend_policy.memory.topic_stop_words", "Topic Stopwords", 7, "One entry per line.", "policy-list-input")}</div>`,
        regexBlock("memory-filler-patterns", "frontend_policy.memory.filler_patterns", "Filler Patterns", "Each regex consists of pattern and flags."),
        regexBlock("memory-non-memory-answer-patterns", "frontend_policy.memory.non_memory_answer_patterns", "Non-Memory Answer Patterns", "Empty lines are discarded.")
      ].join("")
    ),
    group(
      "Model Catalog",
      "frontend_policy.model_catalog",
      [
        `<div class="grid-two">${scrollField("fp-model-llm-seed-models", "frontend_policy.model_catalog.llm_seed_models", "LLM Seed Models", 6, "One model per line.", "policy-list-input")}${scrollField("fp-model-embedding-seed-models", "frontend_policy.model_catalog.embedding_seed_models", "Embedding Seed Models", 4, "One model per line.", "policy-list-input")}</div>`,
        sourceOrderBlock("fp-model-llm-source-order", "frontend_policy.model_catalog.llm_source_order", "LLM Source Order"),
        sourceOrderBlock("fp-model-embedding-source-order", "frontend_policy.model_catalog.embedding_source_order", "Embedding Source Order")
      ].join("")
    ),
    group(
      "Min-Agent Context",
      "frontend_policy.min_agent.context",
      `<div class="grid-two">${numberField("fp-context-history-context-ratio", "frontend_policy.min_agent.context.history_context_ratio", "History Context Ratio", 0.01, 1, 0.01)}${numberField("fp-context-history-token-cap", "frontend_policy.min_agent.context.history_token_cap", "History Token Cap", 1, 10000000)}${numberField("fp-context-system-overhead-tokens", "frontend_policy.min_agent.context.system_overhead_tokens", "System Overhead Tokens", 0, 10000000)}${numberField("fp-context-average-turn-tokens", "frontend_policy.min_agent.context.average_turn_tokens", "Average Turn Tokens", 1, 10000000)}</div>`
    ),
    group(
      "Min-Agent Runtime",
      "frontend_policy.min_agent.runtime",
      `<div class="grid-two">${numberField("fp-runtime-max-tool-rounds", "frontend_policy.min_agent.runtime.max_tool_rounds", "Max. Tool Rounds", 1, 256)}${numberField("fp-runtime-max-sql-rows", "frontend_policy.min_agent.runtime.max_sql_rows", "Max. SQL Rows", 1, 10000)}${numberField("fp-runtime-max-text-length", "frontend_policy.min_agent.runtime.max_text_length", "Max. Text Length", 1, 500000)}${numberField("fp-runtime-max-field-count", "frontend_policy.min_agent.runtime.max_field_count", "Max. Field Count", 1, 10000)}${numberField("fp-runtime-max-evidence-count", "frontend_policy.min_agent.runtime.max_evidence_count", "Max. Evidence Count", 1, 10000)}${numberField("fp-runtime-max-row-count", "frontend_policy.min_agent.runtime.max_row_count", "Max. Row Count", 1, 10000)}${numberField("fp-runtime-max-workbench-output", "frontend_policy.min_agent.runtime.max_workbench_output", "Max. Workbench Output", 256, 1000000)}${numberField("fp-runtime-default-workbench-timeout-ms", "frontend_policy.min_agent.runtime.default_workbench_timeout_ms", "Workbench Timeout (ms)", 1000, 30000)}</div>`
    ),
  ].join("");
}
