import {
  getCurrentConfig,
  getModels,
  deleteApiKey,
  logoutOAuth,
  saveConfig,
  testEmbedding,
  testLlm,
  unlockConfig
} from "../api/client.ts";
import providerCatalog from "../../shared/provider_catalog.ts";
import { createConfigDomAdapter } from "./adapter.ts";
import { createConfigWorkflow } from "./workflow.ts";
import type { ConfigApi, ConfigApp, ConfigAppOptions, ProviderCatalogShape, Section } from "./types.ts";

const DEFAULT_API: ConfigApi = { getCurrentConfig, getModels, deleteApiKey, logoutOAuth, saveConfig, testEmbedding, testLlm, unlockConfig };
const DEFAULT_PROVIDER_CATALOG = providerCatalog as ProviderCatalogShape;

function bindSectionProviderChanges(
  section: Section,
  adapter: ReturnType<typeof createConfigDomAdapter>,
  workflow: ReturnType<typeof createConfigWorkflow>
): void {
  adapter.dom.sections[section].providerInput?.addEventListener("change", (event) => {
    workflow.applyProviderAutoFill(section, (event.currentTarget as HTMLSelectElement).value);
  });
}

function bindEvents(
  adapter: ReturnType<typeof createConfigDomAdapter>,
  workflow: ReturnType<typeof createConfigWorkflow>
): void {
  adapter.dom.formEl?.addEventListener("submit", (event) => {
    event.preventDefault();
    void workflow.submitSave();
  });
  adapter.dom.sections.llm.refreshButton?.addEventListener("click", () => void workflow.refreshModels("llm"));
  adapter.dom.sections.embedding.refreshButton?.addEventListener("click", () => void workflow.refreshModels("embedding"));
  adapter.dom.sections.llm.keyDelete?.addEventListener("click", () => void workflow.deleteApiKey("llm"));
  adapter.dom.sections.embedding.keyDelete?.addEventListener("click", () => void workflow.deleteApiKey("embedding"));
  adapter.dom.sections.llm.testButton?.addEventListener("click", () => void workflow.runLlmTest());
  adapter.dom.sections.embedding.testButton?.addEventListener("click", () => void workflow.runEmbeddingTest());
  adapter.dom.retestButton?.addEventListener("click", async () => {
    if (!adapter.dom.sections.llm.testButton?.disabled) {
      await workflow.runLlmTest();
    }
    await workflow.runEmbeddingTest();
  });
  adapter.dom.credentials.loginButton?.addEventListener("click", () => workflow.loginWithOAuth());
  adapter.dom.credentials.logoutButton?.addEventListener("click", () => void workflow.logoutFromOAuth());
  adapter.dom.sections.llm.keyToggle?.addEventListener("click", () => adapter.toggleSecret("llm"));
  adapter.dom.sections.embedding.keyToggle?.addEventListener("click", () => adapter.toggleSecret("embedding"));
  adapter.dom.adminSecretToggle?.addEventListener("click", () => adapter.toggleSecret("admin"));
  adapter.dom.unlockButton?.addEventListener("click", () => void workflow.submitUnlock());
  adapter.dom.unlockInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") void workflow.submitUnlock();
  });
  bindSectionProviderChanges("llm", adapter, workflow);
  bindSectionProviderChanges("embedding", adapter, workflow);
  adapter.dom.sections.llm.modelInput?.addEventListener("change", () => workflow.updateContextHint());
  adapter.dom.contextLimitInput?.addEventListener("input", () => workflow.updateContextHint());
}

export function createConfigApp(options: ConfigAppOptions = {}): ConfigApp {
  const document = options.document ?? globalThis.document;
  const api = options.api ?? DEFAULT_API;
  const catalog = options.providerCatalog ?? DEFAULT_PROVIDER_CATALOG;
  const adapter = createConfigDomAdapter(document);
  const workflow = createConfigWorkflow({ api, adapter, catalog });

  bindEvents(adapter, workflow);

  return {
    boot: workflow.boot,
    collectPayload: adapter.collectPayload,
    loginWithOAuth: workflow.loginWithOAuth,
    logoutFromOAuth: workflow.logoutFromOAuth,
    refreshModels: workflow.refreshModels,
    deleteApiKey: workflow.deleteApiKey,
    runLlmTest: workflow.runLlmTest,
    runEmbeddingTest: workflow.runEmbeddingTest,
    submitSave: workflow.submitSave,
    submitUnlock: workflow.submitUnlock,
    setSaveStatus: workflow.setSaveStatus,
    getState: workflow.getState
  };
}
