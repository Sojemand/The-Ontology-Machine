import type { FrontendPolicy, FrontendPolicyDiagnostics } from "./frontend_policy.ts";
import type {
  KernelClientFrontendEventBatch,
  KernelDialogState,
  KernelInteractionRouteResponse,
  KernelMirrorEvent,
  KernelProgressEvent,
  KernelUserInteractionRequest,
  KernelUserInteractionResponse,
  KernelWorkflowRunSummary,
  KernelRuntimeResetResponse,
  PipelineManagerState
} from "./pipeline.ts";

export interface Source {
  id: string;
  source_key?: string;
  title: string;
  type: string | null;
  date: string | null;
  actor: string | null;
  source_page?: number | null;
  source_page_count?: number | null;
  page: number;
  page_count: number;
  source_refs: string[];
  snippet: string;
  image_url: string;
  viewer_available?: boolean;
  file_name?: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
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

export interface TokenUsage {
  estimated: boolean;
  input_tokens: number;
  output_tokens: number;
  llm_calls?: number;
}

export interface HealthResponse {
  status: string;
  corpus_docs: number;
  llm_model: string;
  customer_name: string;
  agent_name: string;
  theme: "dark" | "light";
  llm_ready: boolean;
  embedding_ready: boolean;
  database_status?: DatabaseStatus;
  llm_auth_mode: "api_keys" | "oauth";
  oauth_session: OAuthSessionState;
  pipeline_manager: PipelineManagerState | null;
  context_limit: number;
  memory_turns: number;
}

export interface DatabaseStatus {
  base_graph: {
    available: boolean;
    dirty?: boolean;
    document_count?: number;
    unmapped_document_count?: number;
    source_document_count?: number;
    source_page_count?: number;
    structural_unit_count?: number;
    base_unit_count?: number;
    page_unit_count?: number;
    relation_count?: number;
  };
  ontology_lenses: {
    available: boolean;
    count: number;
    active_count?: number;
    primary_ontology_id?: string | null;
  };
}

export interface OAuthSessionState {
  status: "logged_out" | "connected" | "error";
  account_label: string;
  status_message: string;
  client_id_hint: string;
  scope: string;
  expires_at: string;
  account_id: string;
  has_refresh_token: boolean;
}

export interface CredentialTargetState {
  has_secret: boolean;
  ready: boolean;
  source: string;
  fallback_available: boolean;
  message: string;
}

export interface ModelCatalogGroupState {
  models: string[];
  refreshed_at: string;
  source: string;
}

export interface CredentialState {
  auth_mode: "api_keys" | "oauth";
  oauth_supported?: boolean;
  oauth_provider_label?: string;
  oauth_session: OAuthSessionState;
  targets: {
    llm_shared: CredentialTargetState;
    embeddings: CredentialTargetState;
  };
  model_catalog: {
    llm_shared: ModelCatalogGroupState;
    embeddings: ModelCatalogGroupState;
  };
}

export interface ConfigResponse {
  customer_name: string;
  sql_database_path: string;
  pipeline_root: string;
  llm_provider: string;
  llm_base_url: string;
  llm_model: string;
  llm_api_key: string;
  embedding_provider: string;
  embedding_base_url: string;
  embedding_model: string;
  embedding_api_key: string;
  port: number;
  theme: "dark" | "light";
  admin_secret: string;
  protected: boolean;
  context_limit: number;
  frontend_policy: FrontendPolicy;
  frontend_policy_diagnostics?: FrontendPolicyDiagnostics;
  credential_state: CredentialState;
}

export interface ModelsResponse {
  llm_models: string[];
  embedding_models: string[];
  context_limits: Record<string, number | null>;
  source: "live" | "fallback" | "cache" | "seed";
  error?: string;
  updated_at: string;
}

export interface ConnectionTestResponse {
  status: "ok" | "error";
  message: string;
}

export interface ChatHistoryEntry {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface ChatHistoryResponse {
  chats: ChatHistoryEntry[];
}

export interface ChatRestoreResponse {
  messages: Array<{
    role: string;
    content: string;
    sources?: Source[];
    mode?: ChatResponse["mode"];
    exactness?: ChatResponse["exactness"];
    metrics?: ChatResponse["metrics"];
    ambiguities?: ChatResponse["ambiguities"];
    method?: ChatResponse["method"];
    token_usage?: TokenUsage;
  }>;
  title: string;
}

export type { FrontendPolicy, FrontendPolicyDiagnostics } from "./frontend_policy.ts";
export type {
  KernelClientFrontendEventBatch,
  KernelDialogState,
  KernelInteractionRouteResponse,
  KernelMirrorEvent,
  KernelProgressEvent,
  KernelUserInteractionRequest,
  KernelUserInteractionResponse,
  KernelWorkflowRunSummary,
  KernelRuntimeResetResponse,
  PipelineManagerState,
  PipelinePreflightFailure,
  PipelineRunCancelResponse,
  PipelineRunSnapshot,
  PipelineRunState,
  PipelineStageSnapshot
} from "./pipeline.ts";
