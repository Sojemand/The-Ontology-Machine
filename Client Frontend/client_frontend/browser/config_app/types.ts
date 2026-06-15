import type {
  getCurrentConfig,
  getModels,
  deleteApiKey,
  logoutOAuth,
  saveConfig,
  testEmbedding,
  testLlm,
  unlockConfig
} from "../api/client.ts";
import type { ConfigResponse } from "../types/index.ts";
import type { FrontendPolicy } from "../types/frontend_policy.ts";
import type { FrontendPolicyDomRefs } from "./frontend_policy_field.ts";

export type Section = "llm" | "embedding";
export type StatusMode = "ok" | "error" | "idle";
export type SecretField = "llm" | "embedding" | "admin";
export type SectionTokenField = "refreshToken" | "testToken" | "deleteToken";

export interface ConfigApi {
  getCurrentConfig: typeof getCurrentConfig;
  getModels: typeof getModels;
  deleteApiKey: typeof deleteApiKey;
  logoutOAuth: typeof logoutOAuth;
  saveConfig: typeof saveConfig;
  testEmbedding: typeof testEmbedding;
  testLlm: typeof testLlm;
  unlockConfig: typeof unlockConfig;
}

export interface ProviderCatalogShape {
  providers?: Array<{
    provider_id: string;
    display_name: string;
    llm_enabled?: boolean;
    embeddings_enabled?: boolean;
    oauth_supported?: boolean;
    ui_note?: string;
  }>;
  default_base_urls: Record<string, string>;
  context_limits: Record<string, number | null>;
  pricing: Record<string, { input: number; output: number }>;
}

export interface ConfigAppOptions {
  api?: ConfigApi;
  document?: Document;
  providerCatalog?: ProviderCatalogShape;
}

export interface ConfigFormPayload extends Record<string, unknown> {
  customer_name: string;
  sql_database_path: string;
  pipeline_root: string;
  port: number;
  theme: string;
  llm_provider: string;
  llm_base_url: string;
  llm_model: string;
  llm_api_key: string;
  embedding_provider: string;
  embedding_base_url: string;
  embedding_model: string;
  embedding_api_key: string;
  admin_secret: string;
  context_limit: number;
  frontend_policy: FrontendPolicy;
}

export interface ConfigAppState {
  currentConfig: ConfigResponse | null;
  unlocked: boolean;
  llmModels: string[];
  embeddingModels: string[];
  llmContextLimits: Record<string, number | null>;
}

export interface ConfigApp {
  boot(): Promise<void>;
  collectPayload(): ConfigFormPayload;
  loginWithOAuth(): void;
  logoutFromOAuth(): Promise<void>;
  refreshModels(section: Section): Promise<unknown>;
  deleteApiKey(section: Section): Promise<void>;
  runLlmTest(): Promise<unknown>;
  runEmbeddingTest(): Promise<unknown>;
  submitSave(): Promise<void>;
  submitUnlock(secretOverride?: string): Promise<void>;
  setSaveStatus(text: string, mode?: StatusMode): void;
  getState(): ConfigAppState;
}

export interface SectionDomRefs {
  providerInput: HTMLSelectElement | null;
  baseUrlInput: HTMLInputElement | null;
  apiKeyInput: HTMLInputElement | null;
  apiKeyCurrent: HTMLElement | null;
  modelInput: HTMLSelectElement | null;
  statusEl: HTMLParagraphElement | null;
  refreshButton: HTMLButtonElement | null;
  testButton: HTMLButtonElement | null;
  keyDelete: HTMLButtonElement | null;
  keyToggle: HTMLButtonElement | null;
}

export interface CredentialDomRefs {
  statusEl: HTMLParagraphElement | null;
  modeEl: HTMLElement | null;
  accountEl: HTMLElement | null;
  expiresEl: HTMLElement | null;
  refreshEl: HTMLElement | null;
  loginButton: HTMLButtonElement | null;
  logoutButton: HTMLButtonElement | null;
}

export interface DomRefs {
  configTitleEl: HTMLHeadingElement | null;
  formEl: HTMLFormElement | null;
  customerNameInput: HTMLTextAreaElement | null;
  sqlDatabasePathInput: HTMLInputElement | null;
  pipelineRootInput: HTMLInputElement | null;
  portInput: HTMLInputElement | null;
  themeInput: HTMLSelectElement | null;
  credentials: CredentialDomRefs;
  sections: Record<Section, SectionDomRefs>;
  saveStatusEl: HTMLParagraphElement | null;
  saveButton: HTMLButtonElement | null;
  retestButton: HTMLButtonElement | null;
  lockBarEl: HTMLElement | null;
  unlockInput: HTMLInputElement | null;
  unlockButton: HTMLButtonElement | null;
  unlockStatusEl: HTMLParagraphElement | null;
  adminSecretInput: HTMLInputElement | null;
  adminSecretCurrent: HTMLElement | null;
  adminSecretToggle: HTMLButtonElement | null;
  contextLimitInput: HTMLInputElement | null;
  contextLimitHint: HTMLElement | null;
  frontendPolicy: FrontendPolicyDomRefs;
}

export interface SectionState {
  models: string[];
  contextLimits: Record<string, number | null>;
  refreshToken: number;
  testToken: number;
  deleteToken: number;
}

export interface ConfigDomAdapter {
  document: Document;
  dom: DomRefs;
  collectPayload(): ConfigFormPayload;
  applyConfig(config: ConfigResponse): void;
  applyLockState(locked: boolean): void;
  renderModelSelect(section: Section, models: string[], selected: string): void;
  setSectionStatus(section: Section, text: string, mode?: StatusMode): void;
  setSaveStatus(text: string, mode?: StatusMode): void;
  setCredentialStatus(text: string, mode?: StatusMode): void;
  setFrontendPolicyStatus(text: string, mode?: StatusMode, policyPath?: string): void;
  setUnlockStatus(text: string, mode?: StatusMode): void;
  setContextHint(text: string): void;
  setSaveButtonDisabled(disabled: boolean): void;
  setUnlockButtonDisabled(disabled: boolean): void;
  syncProviderSensitiveStatus(): void;
  getProvider(section: Section): string;
  getSectionBaseUrl(section: Section): string;
  setSectionBaseUrl(section: Section, value: string): void;
  getSectionApiKey(section: Section): string;
  clearSectionApiKey(section: Section): void;
  setSectionApiKeyCurrent(section: Section, text: string): void;
  getSectionModel(section: Section): string;
  getContextLimitValue(): number;
  getUnlockSecret(): string;
  clearUnlockSecret(): void;
  clearSensitiveInputs(): void;
  toggleSecret(field: SecretField): void;
}

export interface ConfigWorkflow {
  boot(): Promise<void>;
  loginWithOAuth(): void;
  logoutFromOAuth(): Promise<void>;
  refreshModels(section: Section): Promise<unknown>;
  deleteApiKey(section: Section): Promise<void>;
  runLlmTest(): Promise<unknown>;
  runEmbeddingTest(): Promise<unknown>;
  submitSave(): Promise<void>;
  submitUnlock(secretOverride?: string): Promise<void>;
  setSaveStatus(text: string, mode?: StatusMode): void;
  updateContextHint(): void;
  applyProviderAutoFill(section: Section, provider: string): void;
  getState(): ConfigAppState;
}
