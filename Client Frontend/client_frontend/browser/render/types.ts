import type { Source, TokenUsage } from "../types/index.ts";

export type UiMessageRole = "user" | "assistant" | "system";

export interface UiMessage {
  role: UiMessageRole;
  content: string;
  sources?: Source[];
  mode?: "exact" | "lookup" | "analytic";
  exactness?: "exact" | "evidence_grounded" | "ambiguous" | "insufficient_evidence";
  metrics?: {
    scope_documents: number;
    matched_documents: number;
    matched_occurrences: number;
    aggregated_values: Record<string, number | null> | null;
  };
  ambiguities?: Array<{
    slot: string;
    candidate_count: number;
    strategy: string;
  }>;
  method?: string;
  token_usage?: TokenUsage;
}

export interface ViewerRenderState {
  selectedSource: Source | null;
  page: number;
  imageFailed: boolean;
}

export interface ViewerPresentation {
  title: string;
  meta: string;
  pageLabel: string;
  placeholderText: string | null;
  imageSrc: string | null;
  disablePrev: boolean;
  disableNext: boolean;
}
