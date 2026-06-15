import type { FrontendPolicy, FrontendPolicyDiagnostics } from "../../types/frontend_policy.ts";

export type PolicyGroupKey =
  | "frontend_policy.chat_history"
  | "frontend_policy.memory"
  | "frontend_policy.model_catalog"
  | "frontend_policy.min_agent.context"
  | "frontend_policy.min_agent.runtime"
  | "frontend_policy.min_agent.prompt"
  | "frontend_policy.ontology_agent.prompt";

export interface RegexListDomRefs {
  rootEl: HTMLElement | null;
  rowsEl: HTMLElement | null;
  addButton: HTMLButtonElement | null;
}

export interface FrontendPolicyDomRefs {
  rootEl: HTMLElement | null;
  statusEl: HTMLParagraphElement | null;
  groups: Record<PolicyGroupKey, HTMLElement | null>;
  chatHistory: {
    maxHistoryInput: HTMLInputElement | null;
    titleMaxLengthInput: HTMLInputElement | null;
  };
  memory: {
    maxSummaryLengthInput: HTMLInputElement | null;
    maxTopicsInput: HTMLInputElement | null;
    maxSearchResultsInput: HTMLInputElement | null;
    maxQueryKeysInput: HTMLInputElement | null;
    maxSearchFetchInput: HTMLInputElement | null;
    recentDaysHighInput: HTMLInputElement | null;
    recentDaysLowInput: HTMLInputElement | null;
    queryStopWordsInput: HTMLTextAreaElement | null;
    topicStopWordsInput: HTMLTextAreaElement | null;
    fillerPatterns: RegexListDomRefs;
    nonMemoryAnswerPatterns: RegexListDomRefs;
  };
  modelCatalog: {
    llmSeedModelsInput: HTMLTextAreaElement | null;
    embeddingSeedModelsInput: HTMLTextAreaElement | null;
    llmSourceOrderInputs: HTMLSelectElement[];
    embeddingSourceOrderInputs: HTMLSelectElement[];
  };
  minAgentContext: {
    historyContextRatioInput: HTMLInputElement | null;
    historyTokenCapInput: HTMLInputElement | null;
    systemOverheadTokensInput: HTMLInputElement | null;
    averageTurnTokensInput: HTMLInputElement | null;
  };
  minAgentRuntime: {
    maxToolRoundsInput: HTMLInputElement | null;
    maxSqlRowsInput: HTMLInputElement | null;
    maxTextLengthInput: HTMLInputElement | null;
    maxFieldCountInput: HTMLInputElement | null;
    maxEvidenceCountInput: HTMLInputElement | null;
    maxRowCountInput: HTMLInputElement | null;
    maxWorkbenchOutputInput: HTMLInputElement | null;
    defaultWorkbenchTimeoutInput: HTMLInputElement | null;
  };
  minAgentPrompt: Record<string, HTMLTextAreaElement | null>;
  ontologyAgentPrompt: Record<string, HTMLTextAreaElement | null>;
}

export interface FrontendPolicyErrorDetails {
  message: string;
  policyPath?: string;
}

export interface FrontendPolicyApplyInput {
  frontend_policy: FrontendPolicy;
  frontend_policy_diagnostics?: FrontendPolicyDiagnostics;
}
