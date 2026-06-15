import { ONTOLOGY_PROMPT_FIELD_ORDER, PROMPT_FIELD_ORDER } from "./constants.ts";
import { bindRegexList, renderRegexRows } from "./regex_editor.ts";
import { collectFrontendPolicy, FrontendPolicyInputError } from "./serializer.ts";
import { buildDiagnosticsMessage, setFrontendPolicyStatus } from "./status.ts";
import { buildFrontendPolicyFormMarkup, buildPromptPolicyFormMarkup } from "./template.ts";
import type { FrontendPolicyApplyInput, FrontendPolicyDomRefs, FrontendPolicyErrorDetails, RegexListDomRefs } from "./types.ts";

function queryRegexList(rootEl: HTMLElement | null, listKey: string, path: string): RegexListDomRefs {
  return {
    rootEl: rootEl?.querySelector<HTMLElement>(`[data-policy-path-prefix="${path}"]`) || null,
    rowsEl: rootEl?.querySelector<HTMLElement>(`[data-regex-rows="${listKey}"]`) || rootEl?.querySelector<HTMLElement>(`#fp-${listKey}-rows`) || null,
    addButton: rootEl?.querySelector<HTMLButtonElement>(`[data-add-regex="${listKey}"]`) || null
  };
}

function setTextAreaValue(element: HTMLTextAreaElement | null, values: string[]): void {
  if (element) {
    element.value = values.join("\n");
  }
}

function setSelectValues(inputs: HTMLSelectElement[], values: string[]): void {
  inputs.forEach((input, index) => {
    if (values[index] != null) {
      input.value = values[index];
    }
  });
}

export function queryFrontendPolicyDom(document: Document): FrontendPolicyDomRefs {
  const advancedRootEl = document.querySelector<HTMLElement>("#frontend-policy-form");
  const promptRootEl = document.querySelector<HTMLElement>("#prompt-policy-form");
  if (advancedRootEl && !advancedRootEl.firstElementChild) {
    advancedRootEl.innerHTML = buildFrontendPolicyFormMarkup();
  }
  if (promptRootEl && !promptRootEl.firstElementChild) {
    promptRootEl.innerHTML = buildPromptPolicyFormMarkup();
  }
  bindPromptTabs(promptRootEl);
  const rootEl = document.querySelector<HTMLElement>("#config-form") || advancedRootEl || promptRootEl;
  const dom: FrontendPolicyDomRefs = {
    rootEl,
    statusEl: document.querySelector<HTMLParagraphElement>("#frontend-policy-status"),
    groups: {
      "frontend_policy.chat_history": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.chat_history"]') || null,
      "frontend_policy.memory": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.memory"]') || null,
      "frontend_policy.model_catalog": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.model_catalog"]') || null,
      "frontend_policy.min_agent.context": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.min_agent.context"]') || null,
      "frontend_policy.min_agent.runtime": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.min_agent.runtime"]') || null,
      "frontend_policy.min_agent.prompt": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.min_agent.prompt"]') || null,
      "frontend_policy.ontology_agent.prompt": rootEl?.querySelector('[data-policy-path-prefix="frontend_policy.ontology_agent.prompt"]') || null
    },
    chatHistory: {
      maxHistoryInput: rootEl?.querySelector<HTMLInputElement>("#fp-chat-max-history") || null,
      titleMaxLengthInput: rootEl?.querySelector<HTMLInputElement>("#fp-chat-title-max-length") || null
    },
    memory: {
      maxSummaryLengthInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-max-summary-length") || null,
      maxTopicsInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-max-topics") || null,
      maxSearchResultsInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-max-search-results") || null,
      maxQueryKeysInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-max-query-keys") || null,
      maxSearchFetchInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-max-search-fetch") || null,
      recentDaysHighInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-recent-days-high") || null,
      recentDaysLowInput: rootEl?.querySelector<HTMLInputElement>("#fp-memory-recent-days-low") || null,
      queryStopWordsInput: rootEl?.querySelector<HTMLTextAreaElement>("#fp-memory-query-stop-words") || null,
      topicStopWordsInput: rootEl?.querySelector<HTMLTextAreaElement>("#fp-memory-topic-stop-words") || null,
      fillerPatterns: queryRegexList(advancedRootEl, "memory-filler-patterns", "frontend_policy.memory.filler_patterns"),
      nonMemoryAnswerPatterns: queryRegexList(advancedRootEl, "memory-non-memory-answer-patterns", "frontend_policy.memory.non_memory_answer_patterns")
    },
    modelCatalog: {
      llmSeedModelsInput: rootEl?.querySelector<HTMLTextAreaElement>("#fp-model-llm-seed-models") || null,
      embeddingSeedModelsInput: rootEl?.querySelector<HTMLTextAreaElement>("#fp-model-embedding-seed-models") || null,
      llmSourceOrderInputs: Array.from(rootEl?.querySelectorAll<HTMLSelectElement>('[id^="fp-model-llm-source-order-"]') || []),
      embeddingSourceOrderInputs: Array.from(rootEl?.querySelectorAll<HTMLSelectElement>('[id^="fp-model-embedding-source-order-"]') || [])
    },
    minAgentContext: {
      historyContextRatioInput: rootEl?.querySelector<HTMLInputElement>("#fp-context-history-context-ratio") || null,
      historyTokenCapInput: rootEl?.querySelector<HTMLInputElement>("#fp-context-history-token-cap") || null,
      systemOverheadTokensInput: rootEl?.querySelector<HTMLInputElement>("#fp-context-system-overhead-tokens") || null,
      averageTurnTokensInput: rootEl?.querySelector<HTMLInputElement>("#fp-context-average-turn-tokens") || null
    },
    minAgentRuntime: {
      maxToolRoundsInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-tool-rounds") || null,
      maxSqlRowsInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-sql-rows") || null,
      maxTextLengthInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-text-length") || null,
      maxFieldCountInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-field-count") || null,
      maxEvidenceCountInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-evidence-count") || null,
      maxRowCountInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-row-count") || null,
      maxWorkbenchOutputInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-max-workbench-output") || null,
      defaultWorkbenchTimeoutInput: rootEl?.querySelector<HTMLInputElement>("#fp-runtime-default-workbench-timeout-ms") || null
    },
    minAgentPrompt: Object.fromEntries(PROMPT_FIELD_ORDER.map(([key]) => [key, promptRootEl?.querySelector<HTMLTextAreaElement>(`#fp-prompt-${key}`) || null])),
    ontologyAgentPrompt: Object.fromEntries(ONTOLOGY_PROMPT_FIELD_ORDER.map(([key]) => [key, promptRootEl?.querySelector<HTMLTextAreaElement>(`#fp-ontology-prompt-${key}`) || null]))
  };
  bindRegexList(dom.memory.fillerPatterns, "frontend_policy.memory.filler_patterns");
  bindRegexList(dom.memory.nonMemoryAnswerPatterns, "frontend_policy.memory.non_memory_answer_patterns");
  return dom;
}

function bindPromptTabs(rootEl: HTMLElement | null): void {
  if (!rootEl || rootEl.dataset.promptTabsBound === "1") return;
  rootEl.dataset.promptTabsBound = "1";
  const activate = (target: string) => {
    rootEl.querySelectorAll<HTMLButtonElement>("[data-policy-prompt-tab]").forEach((button) => {
      button.setAttribute("aria-selected", String(button.dataset.policyPromptTab === target));
    });
    rootEl.querySelectorAll<HTMLElement>("[data-policy-prompt-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.policyPromptPanel !== target;
    });
  };
  rootEl.querySelectorAll<HTMLButtonElement>("[data-policy-prompt-tab]").forEach((button) => {
    button.addEventListener("click", () => activate(button.dataset.policyPromptTab || "query"));
  });
  activate(rootEl.querySelector<HTMLButtonElement>('[data-policy-prompt-tab][aria-selected="true"]')?.dataset.policyPromptTab || "query");
}

export function collectFrontendPolicyValue(dom: FrontendPolicyDomRefs) {
  return collectFrontendPolicy(dom);
}

export function applyFrontendPolicyValue(dom: FrontendPolicyDomRefs, config: FrontendPolicyApplyInput): void {
  const policy = config.frontend_policy;
  if (dom.chatHistory.maxHistoryInput) dom.chatHistory.maxHistoryInput.value = String(policy.chat_history.max_history);
  if (dom.chatHistory.titleMaxLengthInput) dom.chatHistory.titleMaxLengthInput.value = String(policy.chat_history.title_max_length);
  if (dom.memory.maxSummaryLengthInput) dom.memory.maxSummaryLengthInput.value = String(policy.memory.max_summary_length);
  if (dom.memory.maxTopicsInput) dom.memory.maxTopicsInput.value = String(policy.memory.max_topics);
  if (dom.memory.maxSearchResultsInput) dom.memory.maxSearchResultsInput.value = String(policy.memory.max_search_results);
  if (dom.memory.maxQueryKeysInput) dom.memory.maxQueryKeysInput.value = String(policy.memory.max_query_keys);
  if (dom.memory.maxSearchFetchInput) dom.memory.maxSearchFetchInput.value = String(policy.memory.max_search_fetch);
  if (dom.memory.recentDaysHighInput) dom.memory.recentDaysHighInput.value = String(policy.memory.recent_days_high);
  if (dom.memory.recentDaysLowInput) dom.memory.recentDaysLowInput.value = String(policy.memory.recent_days_low);
  setTextAreaValue(dom.memory.queryStopWordsInput, policy.memory.query_stop_words);
  setTextAreaValue(dom.memory.topicStopWordsInput, policy.memory.topic_stop_words);
  renderRegexRows(dom.memory.fillerPatterns, "frontend_policy.memory.filler_patterns", policy.memory.filler_patterns);
  renderRegexRows(dom.memory.nonMemoryAnswerPatterns, "frontend_policy.memory.non_memory_answer_patterns", policy.memory.non_memory_answer_patterns);
  setTextAreaValue(dom.modelCatalog.llmSeedModelsInput, policy.model_catalog.llm_seed_models);
  setTextAreaValue(dom.modelCatalog.embeddingSeedModelsInput, policy.model_catalog.embedding_seed_models);
  setSelectValues(dom.modelCatalog.llmSourceOrderInputs, policy.model_catalog.llm_source_order);
  setSelectValues(dom.modelCatalog.embeddingSourceOrderInputs, policy.model_catalog.embedding_source_order);
  if (dom.minAgentContext.historyContextRatioInput) dom.minAgentContext.historyContextRatioInput.value = String(policy.min_agent.context.history_context_ratio);
  if (dom.minAgentContext.historyTokenCapInput) dom.minAgentContext.historyTokenCapInput.value = String(policy.min_agent.context.history_token_cap);
  if (dom.minAgentContext.systemOverheadTokensInput) dom.minAgentContext.systemOverheadTokensInput.value = String(policy.min_agent.context.system_overhead_tokens);
  if (dom.minAgentContext.averageTurnTokensInput) dom.minAgentContext.averageTurnTokensInput.value = String(policy.min_agent.context.average_turn_tokens);
  if (dom.minAgentRuntime.maxToolRoundsInput) dom.minAgentRuntime.maxToolRoundsInput.value = String(policy.min_agent.runtime.max_tool_rounds);
  if (dom.minAgentRuntime.maxSqlRowsInput) dom.minAgentRuntime.maxSqlRowsInput.value = String(policy.min_agent.runtime.max_sql_rows);
  if (dom.minAgentRuntime.maxTextLengthInput) dom.minAgentRuntime.maxTextLengthInput.value = String(policy.min_agent.runtime.max_text_length);
  if (dom.minAgentRuntime.maxFieldCountInput) dom.minAgentRuntime.maxFieldCountInput.value = String(policy.min_agent.runtime.max_field_count);
  if (dom.minAgentRuntime.maxEvidenceCountInput) dom.minAgentRuntime.maxEvidenceCountInput.value = String(policy.min_agent.runtime.max_evidence_count);
  if (dom.minAgentRuntime.maxRowCountInput) dom.minAgentRuntime.maxRowCountInput.value = String(policy.min_agent.runtime.max_row_count);
  if (dom.minAgentRuntime.maxWorkbenchOutputInput) dom.minAgentRuntime.maxWorkbenchOutputInput.value = String(policy.min_agent.runtime.max_workbench_output);
  if (dom.minAgentRuntime.defaultWorkbenchTimeoutInput) dom.minAgentRuntime.defaultWorkbenchTimeoutInput.value = String(policy.min_agent.runtime.default_workbench_timeout_ms);
  PROMPT_FIELD_ORDER.forEach(([key]) => {
    if (dom.minAgentPrompt[key]) {
      dom.minAgentPrompt[key].value = policy.min_agent.prompt[key];
    }
  });
  ONTOLOGY_PROMPT_FIELD_ORDER.forEach(([key]) => {
    if (dom.ontologyAgentPrompt[key]) {
      dom.ontologyAgentPrompt[key].value = policy.ontology_agent.prompt[key];
    }
  });
  setFrontendPolicyStatus(dom, buildDiagnosticsMessage(config.frontend_policy_diagnostics), config.frontend_policy_diagnostics ? "error" : "idle", config.frontend_policy_diagnostics?.policy_path);
}

export function setFrontendPolicyFieldStatus(dom: FrontendPolicyDomRefs, text: string, mode = "idle", policyPath?: string): void {
  setFrontendPolicyStatus(dom, text, mode, policyPath);
}

export function extractFrontendPolicyError(error: unknown): FrontendPolicyErrorDetails | null {
  if (error instanceof FrontendPolicyInputError) {
    return { message: error.message, policyPath: error.policyPath };
  }
  const payload = typeof error === "object" && error && "payload" in error ? (error as { payload?: Record<string, unknown> | null }).payload : null;
  if (payload?.field === "frontend_policy") {
    return {
      message: typeof payload.error === "string" ? payload.error : typeof payload.message === "string" ? payload.message : "Frontend policy is invalid.",
      policyPath: typeof payload.policy_path === "string" ? payload.policy_path : undefined
    };
  }
  return null;
}
