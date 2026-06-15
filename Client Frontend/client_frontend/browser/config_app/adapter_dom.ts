import providerCatalog from "../../shared/provider_catalog.ts";
import { queryCredentialDom } from "./credentials_view.ts";
import { queryFrontendPolicyDom } from "./frontend_policy_field.ts";
import type { DomRefs, Section, SectionDomRefs, StatusMode } from "./types.ts";

function querySectionDom(document: Document, section: Section): SectionDomRefs {
  return {
    providerInput: document.querySelector<HTMLSelectElement>(`#${section}-provider`),
    baseUrlInput: document.querySelector<HTMLInputElement>(`#${section}-base-url`),
    apiKeyInput: document.querySelector<HTMLInputElement>(`#${section}-api-key`),
    apiKeyCurrent: document.querySelector<HTMLElement>(`#${section}-api-key-current`),
    modelInput: document.querySelector<HTMLSelectElement>(`#${section}-model`),
    statusEl: document.querySelector<HTMLParagraphElement>(`#${section}-status`),
    refreshButton: document.querySelector<HTMLButtonElement>(`#${section}-refresh`),
    testButton: document.querySelector<HTMLButtonElement>(`#${section}-test`),
    keyDelete: document.querySelector<HTMLButtonElement>(`#${section}-key-delete`),
    keyToggle: document.querySelector<HTMLButtonElement>(`#${section}-key-toggle`)
  };
}

export function initializeConfigTabs(document: Document): void {
  const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-config-tab]"));
  const panels = Array.from(document.querySelectorAll<HTMLElement>("[data-config-panel]"));
  if (!tabs.length || !panels.length) return;
  const root = document.documentElement;
  if (root.dataset.configTabsBound === "1") return;
  root.dataset.configTabsBound = "1";
  const activate = (target: string) => {
    document.querySelectorAll<HTMLButtonElement>("[data-config-tab]").forEach((button) => {
      button.setAttribute("aria-selected", String(button.dataset.configTab === target));
    });
    document.querySelectorAll<HTMLElement>("[data-config-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.configPanel !== target;
    });
  };
  tabs.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      activate(button.dataset.configTab || "setup");
    });
  });
  activate(tabs.find((button) => button.getAttribute("aria-selected") === "true")?.dataset.configTab || "setup");
}

function providerTarget(section: Section): "llm" | "embeddings" {
  return section === "embedding" ? "embeddings" : "llm";
}

export function populateProviderSelect(select: HTMLSelectElement | null, section: Section): void {
  if (!select) return;
  const target = providerTarget(section);
  const providers = ((providerCatalog as { providers?: Array<Record<string, unknown>> }).providers || [])
    .filter((provider) => Boolean(provider[target === "embeddings" ? "embeddings_enabled" : "llm_enabled"]));
  select.replaceChildren(...providers.map((provider) => {
    const option = select.ownerDocument.createElement("option");
    option.value = String(provider.provider_id || "");
    option.textContent = String(provider.display_name || provider.provider_id || "");
    return option;
  }));
}

export function queryDom(document: Document): DomRefs {
  return {
    configTitleEl: document.querySelector<HTMLHeadingElement>("#config-title"),
    formEl: document.querySelector<HTMLFormElement>("#config-form"),
    customerNameInput: document.querySelector<HTMLTextAreaElement>("#customer-name-input"),
    sqlDatabasePathInput: document.querySelector<HTMLInputElement>("#sql-database-path-input"),
    pipelineRootInput: document.querySelector<HTMLInputElement>("#pipeline-root-input"),
    portInput: document.querySelector<HTMLInputElement>("#port-input"),
    themeInput: document.querySelector<HTMLSelectElement>("#theme-input"),
    credentials: queryCredentialDom(document),
    sections: {
      llm: querySectionDom(document, "llm"),
      embedding: querySectionDom(document, "embedding")
    },
    saveStatusEl: document.querySelector<HTMLParagraphElement>("#save-status"),
    saveButton: document.querySelector<HTMLButtonElement>("#save-config"),
    retestButton: document.querySelector<HTMLButtonElement>("#retest-config"),
    lockBarEl: document.querySelector<HTMLElement>("#lock-bar"),
    unlockInput: document.querySelector<HTMLInputElement>("#unlock-input"),
    unlockButton: document.querySelector<HTMLButtonElement>("#unlock-button"),
    unlockStatusEl: document.querySelector<HTMLParagraphElement>("#unlock-status"),
    adminSecretInput: document.querySelector<HTMLInputElement>("#admin-secret-input"),
    adminSecretCurrent: document.querySelector<HTMLElement>("#admin-secret-current"),
    adminSecretToggle: document.querySelector<HTMLButtonElement>("#admin-secret-toggle"),
    contextLimitInput: document.querySelector<HTMLInputElement>("#context-limit"),
    contextLimitHint: document.querySelector<HTMLElement>("#context-limit-hint"),
    frontendPolicy: queryFrontendPolicyDom(document)
  };
}

export function setStatus(element: HTMLElement | null, text: string, mode: StatusMode = "idle"): void {
  if (!element) return;
  element.textContent = text;
  element.style.color =
    mode === "ok" ? "var(--success)" : mode === "error" ? "var(--danger)" : "var(--text-muted)";
}
