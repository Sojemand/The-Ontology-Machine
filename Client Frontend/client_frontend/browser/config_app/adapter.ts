import { populateModelSelect } from "../config_select.ts";
import providerCatalog from "../../shared/provider_catalog.ts";
import type { ConfigResponse } from "../types/index.ts";
import { applyCredentialView } from "./credentials_view.ts";
import { initializeConfigTabs, populateProviderSelect, queryDom, setStatus } from "./adapter_dom.ts";
import {
  applyFrontendPolicyValue,
  collectFrontendPolicyValue,
  setFrontendPolicyStatus as setFrontendPolicyFieldStatus
} from "./frontend_policy_field.ts";
import type { ConfigDomAdapter, ConfigFormPayload, Section, SecretField } from "./types.ts";

type ProviderDefinition = {
  provider_id?: string;
  display_name?: string;
  oauth_supported?: boolean;
};

const PROVIDERS = ((providerCatalog as { providers?: ProviderDefinition[] }).providers || []);

function providerDefinition(providerId: string): ProviderDefinition {
  return PROVIDERS.find((provider) => provider.provider_id === providerId) || { provider_id: providerId };
}

function providerLabel(providerId: string): string {
  const definition = providerDefinition(providerId);
  return definition.display_name || definition.provider_id || providerId || "provider";
}

function providerSupportsOAuth(providerId: string): boolean {
  return Boolean(providerDefinition(providerId).oauth_supported);
}

function normalizeBaseUrl(value: string): string {
  return String(value || "").trim().replace(/\/+$/, "");
}

function configProvider(config: ConfigResponse, section: Section): string {
  return section === "embedding" ? config.embedding_provider : config.llm_provider;
}

function configBaseUrl(config: ConfigResponse, section: Section): string {
  return normalizeBaseUrl(section === "embedding" ? config.embedding_base_url : config.llm_base_url);
}

function targetForSection(section: Section): "llm_shared" | "embeddings" {
  return section === "embedding" ? "embeddings" : "llm_shared";
}

export function createConfigDomAdapter(document: Document): ConfigDomAdapter {
  initializeConfigTabs(document);
  const dom = queryDom(document);
  let lastConfig: ConfigResponse | null = null;
  populateProviderSelect(dom.sections.llm.providerInput, "llm");
  populateProviderSelect(dom.sections.embedding.providerInput, "embedding");
  const getSectionDom = (section: Section) => dom.sections[section];
  const getProviderValue = (section: Section) => {
    const legacyRadio = document.querySelector<HTMLInputElement>(`input[name="${section}_provider"]:checked`);
    return legacyRadio?.value.trim() || getSectionDom(section).providerInput?.value.trim() || "openai";
  };
  const setProviderValue = (section: Section, value: string) => {
    const select = getSectionDom(section).providerInput;
    if (select) select.value = value;
    document.querySelectorAll<HTMLInputElement>(`input[name="${section}_provider"]`).forEach((input) => {
      input.checked = input.value === value;
    });
  };
  const sectionMatchesSavedConfig = (section: Section, config: ConfigResponse) => {
    return getProviderValue(section) === configProvider(config, section)
      && normalizeBaseUrl(getSectionDom(section).baseUrlInput?.value || "") === configBaseUrl(config, section);
  };
  const renderApiKeyStatus = (section: Section) => {
    const target = getSectionDom(section);
    if (!lastConfig || !target.apiKeyCurrent) return;
    const selectedProvider = getProviderValue(section);
    const selectedLabel = providerLabel(selectedProvider);
    const typedKey = Boolean(target.apiKeyInput?.value.trim());
    if (!sectionMatchesSavedConfig(section, lastConfig)) {
      target.apiKeyCurrent.textContent = typedKey
        ? `New key will be saved for ${selectedLabel}.`
        : `Save to check provider-specific key for ${selectedLabel}.`;
      return;
    }
    const state = lastConfig.credential_state?.targets?.[targetForSection(section)];
    target.apiKeyCurrent.textContent = state?.has_secret
      ? state.message || `Saved for ${selectedLabel}.`
      : state?.message || `No key saved for ${selectedLabel}.`;
  };
  const renderOAuthStatus = () => {
    if (!lastConfig) return;
    if (sectionMatchesSavedConfig("llm", lastConfig)) {
      applyCredentialView(dom.credentials, lastConfig);
      return;
    }
    const selectedProvider = getProviderValue("llm");
    const selectedLabel = providerLabel(selectedProvider);
    const session = lastConfig.credential_state?.oauth_session;
    if (dom.credentials.modeEl) {
      dom.credentials.modeEl.textContent = providerSupportsOAuth(selectedProvider) ? "Save required" : "Provider API";
    }
    if (dom.credentials.statusEl) {
      dom.credentials.statusEl.textContent = providerSupportsOAuth(selectedProvider)
        ? `Save ${selectedLabel} as the LLM provider before OAuth login.`
        : `OAuth is not available for ${selectedLabel}.`;
    }
    if (dom.credentials.loginButton) dom.credentials.loginButton.disabled = true;
    if (dom.credentials.logoutButton) dom.credentials.logoutButton.disabled = !session || session.status === "logged_out";
  };
  const syncProviderSensitiveStatus = () => {
    renderApiKeyStatus("llm");
    renderApiKeyStatus("embedding");
    renderOAuthStatus();
  };
  dom.sections.llm.providerInput?.addEventListener("change", () => {
    setProviderValue("llm", dom.sections.llm.providerInput?.value || "openai");
    syncProviderSensitiveStatus();
  });
  dom.sections.embedding.providerInput?.addEventListener("change", () => {
    setProviderValue("embedding", dom.sections.embedding.providerInput?.value || "openai");
    syncProviderSensitiveStatus();
  });
  dom.sections.llm.baseUrlInput?.addEventListener("input", syncProviderSensitiveStatus);
  dom.sections.embedding.baseUrlInput?.addEventListener("input", syncProviderSensitiveStatus);
  dom.sections.llm.apiKeyInput?.addEventListener("input", syncProviderSensitiveStatus);
  dom.sections.embedding.apiKeyInput?.addEventListener("input", syncProviderSensitiveStatus);
  const getSecretParts = (field: SecretField) =>
    field === "admin"
      ? { input: dom.adminSecretInput, button: dom.adminSecretToggle }
      : { input: getSectionDom(field).apiKeyInput, button: getSectionDom(field).keyToggle };

  return {
    document,
    dom,
    collectPayload(): ConfigFormPayload {
      return {
        customer_name: dom.customerNameInput?.value.trim() ?? "",
        sql_database_path: dom.sqlDatabasePathInput?.value.trim() ?? "",
        pipeline_root: dom.pipelineRootInput?.value.trim() ?? "",
        port: Number(dom.portInput?.value || 3000),
        theme: dom.themeInput?.value || "dark",
        llm_provider: getProviderValue("llm") || "openai",
        llm_base_url: dom.sections.llm.baseUrlInput?.value.trim() ?? "",
        llm_model: dom.sections.llm.modelInput?.value.trim() ?? "",
        llm_api_key: dom.sections.llm.apiKeyInput?.value.trim() ?? "",
        embedding_provider: getProviderValue("embedding") || "openai",
        embedding_base_url: dom.sections.embedding.baseUrlInput?.value.trim() ?? "",
        embedding_model: dom.sections.embedding.modelInput?.value.trim() ?? "",
        embedding_api_key: dom.sections.embedding.apiKeyInput?.value.trim() ?? "",
        admin_secret: dom.adminSecretInput?.value.trim() ?? "",
        context_limit: Number(dom.contextLimitInput?.value || 127096),
        frontend_policy: collectFrontendPolicyValue(dom.frontendPolicy)
      };
    },
    applyConfig(config) {
      if (dom.configTitleEl) dom.configTitleEl.textContent = config.customer_name;
      if (dom.customerNameInput) dom.customerNameInput.value = config.customer_name;
      if (dom.sqlDatabasePathInput) dom.sqlDatabasePathInput.value = config.sql_database_path;
      if (dom.pipelineRootInput) dom.pipelineRootInput.value = config.pipeline_root || "";
      if (dom.portInput) dom.portInput.value = String(config.port);
      if (dom.themeInput) dom.themeInput.value = config.theme;
      lastConfig = config;
      setProviderValue("llm", config.llm_provider);
      setProviderValue("embedding", config.embedding_provider);
      if (dom.sections.llm.baseUrlInput) dom.sections.llm.baseUrlInput.value = config.llm_base_url;
      if (dom.sections.embedding.baseUrlInput) dom.sections.embedding.baseUrlInput.value = config.embedding_base_url;
      if (dom.sections.llm.testButton) dom.sections.llm.testButton.disabled = config.credential_state?.auth_mode === "oauth";
      if (dom.adminSecretCurrent) {
        dom.adminSecretCurrent.textContent = config.admin_secret
          ? "Saved."
          : "No password set - configuration is open.";
      }
      if (dom.contextLimitInput) dom.contextLimitInput.value = String(config.context_limit || 127096);
      applyFrontendPolicyValue(dom.frontendPolicy, config);
      syncProviderSensitiveStatus();
    },
    applyLockState(locked) {
      dom.formEl?.classList.toggle("locked", locked);
      if (dom.lockBarEl) dom.lockBarEl.hidden = !locked;
    },
    renderModelSelect(section, models, selected) {
      populateModelSelect(getSectionDom(section).modelInput, models, selected);
    },
    setSectionStatus(section, text, mode = "idle") {
      setStatus(getSectionDom(section).statusEl, text, mode);
    },
    setSaveStatus(text, mode = "idle") {
      setStatus(dom.saveStatusEl, text, mode);
    },
    setCredentialStatus(text, mode = "idle") {
      setStatus(dom.credentials.statusEl, text, mode);
    },
    setFrontendPolicyStatus(text, mode = "idle", policyPath) {
      setFrontendPolicyFieldStatus(dom.frontendPolicy, text, mode, policyPath);
    },
    setUnlockStatus(text, mode = "idle") {
      setStatus(dom.unlockStatusEl, text, mode);
    },
    setContextHint(text) {
      if (dom.contextLimitHint) dom.contextLimitHint.textContent = text;
    },
    setSaveButtonDisabled(disabled) {
      if (dom.saveButton) dom.saveButton.disabled = disabled;
    },
    setUnlockButtonDisabled(disabled) {
      if (dom.unlockButton) dom.unlockButton.disabled = disabled;
    },
    syncProviderSensitiveStatus,
    getProvider(section) {
      return getProviderValue(section) || "openai";
    },
    getSectionBaseUrl(section) {
      return getSectionDom(section).baseUrlInput?.value.trim() ?? "";
    },
    setSectionBaseUrl(section, value) {
      const input = getSectionDom(section).baseUrlInput;
      if (input) input.value = value;
    },
    getSectionApiKey(section) {
      return getSectionDom(section).apiKeyInput?.value.trim() ?? "";
    },
    clearSectionApiKey(section) {
      const input = getSectionDom(section).apiKeyInput;
      if (input) input.value = "";
    },
    setSectionApiKeyCurrent(section, text) {
      const current = getSectionDom(section).apiKeyCurrent;
      if (current) current.textContent = text;
    },
    getSectionModel(section) {
      return getSectionDom(section).modelInput?.value.trim() ?? "";
    },
    getContextLimitValue() {
      return Number(dom.contextLimitInput?.value || 127096);
    },
    getUnlockSecret() {
      return dom.unlockInput?.value ?? "";
    },
    clearUnlockSecret() {
      if (dom.unlockInput) dom.unlockInput.value = "";
    },
    clearSensitiveInputs() {
      if (dom.sections.llm.apiKeyInput) dom.sections.llm.apiKeyInput.value = "";
      if (dom.sections.embedding.apiKeyInput) dom.sections.embedding.apiKeyInput.value = "";
      if (dom.adminSecretInput) dom.adminSecretInput.value = "";
    },
    toggleSecret(field) {
      const { input, button } = getSecretParts(field);
      if (!input || !button) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
    }
  };
}
