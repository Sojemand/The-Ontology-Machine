import type { ChatHistoryEntry, HealthResponse, KernelDialogState, Source } from "../types/index.ts";
import { renderHistoryListHtml, renderMessagesHtml, renderSourcesHtml, type UiMessage } from "../render.ts";
import { MAIN_APP_DEFAULTS, fitCustomerNameMinSize, STORAGE_KEYS } from "./policy.ts";
import type { ChatAgentType, KernelUiState, LayoutDensity, Theme, TokenCounterPresentation, TurnCounterPresentation, WorkspacePane } from "./types.ts";
import { parseStoredPane, parseStoredTheme } from "./validation.ts";
import { createKernelDialogDomAdapter } from "./kernel_dialog_dom_adapter.ts";
import { createPipelineDomAdapter } from "./pipeline_dom_adapter.ts";
import { queryDom } from "./dom_query.ts";
import type { TaxonomyWorkflowOption } from "./taxonomy_workflow_launcher.ts";

export function createMainDomAdapter(document: Document, windowObject: Window) {
  const dom = queryDom(document);
  const pipelineDom = createPipelineDomAdapter(document, dom);
  const kernelDialogDom = createKernelDialogDomAdapter(document, dom);
  const setTaxonomyWorkflowMenuOpen = (open: boolean) => {
    if (dom.taxonomyWorkflowMenuListEl) dom.taxonomyWorkflowMenuListEl.hidden = !open;
    if (dom.taxonomyWorkflowMenuButtonEl) dom.taxonomyWorkflowMenuButtonEl.setAttribute("aria-expanded", String(open));
  };
  const readStoredNumber = (key: string, fallback: number) => {
    try {
      const parsed = Number(windowObject.localStorage.getItem(key));
      return Number.isFinite(parsed) ? parsed : fallback;
    } catch {
      return fallback;
    }
  };

  return {
    document,
    windowObject,
    dom,
    readStoredPane(): WorkspacePane {
      try {
        return parseStoredPane(windowObject.localStorage.getItem(STORAGE_KEYS.activePane));
      } catch {
        return "chat";
      }
    },
    readStoredTheme(): Theme | null {
      try {
        return parseStoredTheme(windowObject.localStorage.getItem(STORAGE_KEYS.theme));
      } catch {
        return null;
      }
    },
    readStoredNumber,
    writeStoredNumber(key: string, value: number): void {
      try {
        windowObject.localStorage.setItem(key, String(Math.round(value)));
      } catch {}
    },
    writeStoredPane(value: WorkspacePane): void {
      try {
        windowObject.localStorage.setItem(STORAGE_KEYS.activePane, value);
      } catch {}
    },
    writeStoredTheme(value: Theme): void {
      try {
        windowObject.localStorage.setItem(STORAGE_KEYS.theme, value);
      } catch {}
    },
    renderMessages(messages: UiMessage[]): void {
      if (!dom.messagesEl) return;
      dom.messagesEl.innerHTML = renderMessagesHtml(messages);
      dom.messagesEl.scrollTop = dom.messagesEl.scrollHeight;
    },
    renderSources(sources: Source[], selectedSourceId: string | null): void {
      if (!dom.sourcesListEl || !dom.sourceCountEl) return;
      dom.sourceCountEl.textContent = String(sources.length);
      if (!sources.length) {
        dom.sourcesListEl.classList.add("empty-state");
        dom.sourcesListEl.textContent = MAIN_APP_DEFAULTS.emptySources;
        return;
      }
      dom.sourcesListEl.classList.remove("empty-state");
      dom.sourcesListEl.innerHTML = renderSourcesHtml(sources, selectedSourceId);
    },
    renderHistoryList(chats: ChatHistoryEntry[]): void {
      if (dom.historyListEl) dom.historyListEl.innerHTML = renderHistoryListHtml(chats);
    },
    setChatStatus(text: string, spinning = false): void {
      if (!dom.chatStatusEl) return;
      dom.chatStatusEl.textContent = "";
      if (spinning) {
        const dot = document.createElement("span");
        dot.className = "spinner";
        dom.chatStatusEl.appendChild(dot);
      }
      dom.chatStatusEl.appendChild(document.createTextNode(text));
    },
    renderTaxonomyWorkflowOptions(options: TaxonomyWorkflowOption[]): void {
      if (!dom.taxonomyWorkflowMenuListEl) return;
      dom.taxonomyWorkflowMenuListEl.replaceChildren();
      for (const option of options) {
        const item = document.createElement("button");
        const label = document.createElement("span");
        const description = document.createElement("span");
        item.type = "button";
        item.className = "taxonomy-workflow-option";
        item.dataset.toolName = option.toolName;
        item.setAttribute("role", "menuitem");
        item.title = option.description;
        label.className = "taxonomy-workflow-option-label";
        label.textContent = option.label;
        description.className = "taxonomy-workflow-option-description";
        description.textContent = option.description;
        item.append(label, description);
        dom.taxonomyWorkflowMenuListEl.appendChild(item);
      }
    },
    setTaxonomyWorkflowMenuOpen,
    toggleTaxonomyWorkflowMenu(): void {
      setTaxonomyWorkflowMenuOpen(Boolean(dom.taxonomyWorkflowMenuListEl?.hidden));
    },
    setInteractionState(blocked: boolean, historyDisabled: boolean): void {
      if (dom.sendButtonEl) dom.sendButtonEl.disabled = blocked;
      if (dom.newChatBtn) dom.newChatBtn.disabled = blocked;
      if (dom.chatInputEl) {
        const wasDisabled = dom.chatInputEl.disabled;
        dom.chatInputEl.disabled = blocked;
        if (wasDisabled && !blocked) dom.chatInputEl.focus();
      }
      if (dom.historyBtn) dom.historyBtn.disabled = historyDisabled;
      if (dom.taxonomyWorkflowMenuButtonEl) dom.taxonomyWorkflowMenuButtonEl.disabled = blocked;
      if (blocked) setTaxonomyWorkflowMenuOpen(false);
    },
    setTheme(theme: Theme): void {
      document.body.classList.toggle("theme-light", theme === "light");
      document.body.classList.toggle("theme-dark", theme === "dark");
      if (dom.themeToggleEl) dom.themeToggleEl.textContent = theme === "dark" ? "Light" : "Dark";
    },
    setCustomerName(name: string): void {
      if (dom.customerNameEl) dom.customerNameEl.textContent = name;
    },
    fitCustomerName(density: LayoutDensity): void {
      if (!dom.customerNameEl) return;
      dom.customerNameEl.style.fontSize = "";
      const lineHeight = parseFloat(windowObject.getComputedStyle(dom.customerNameEl).lineHeight) || dom.customerNameEl.offsetHeight;
      let size = parseFloat(windowObject.getComputedStyle(dom.customerNameEl).fontSize);
      while (dom.customerNameEl.scrollHeight > lineHeight * 2 + 2 && size > fitCustomerNameMinSize(density)) {
        size -= 1;
        dom.customerNameEl.style.fontSize = `${size}px`;
      }
    },
    setAgentName(name: string): void {
      if (dom.agentNameEl) dom.agentNameEl.textContent = name;
    },
    setActiveAgentTab(agent: ChatAgentType): void {
      dom.agentTabs.forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.agent === agent));
      });
      if (dom.taxonomyWorkflowLauncherEl) dom.taxonomyWorkflowLauncherEl.hidden = agent !== "pipeline";
      if (agent !== "pipeline") setTaxonomyWorkflowMenuOpen(false);
    },
    renderPipelinePermission(health: HealthResponse | null, activeAgent: ChatAgentType, kernelUi: KernelUiState): void {
      pipelineDom.renderPipelinePermission(health, activeAgent, kernelUi);
    },
    setPipelineAbortPending: pipelineDom.setPipelineAbortPending,
    setKernelResetButtonState(visible: boolean, disabled: boolean, pending = false): void {
      if (!dom.kernelResetButtonEl) return;
      dom.kernelResetButtonEl.hidden = !visible;
      dom.kernelResetButtonEl.disabled = disabled || pending;
      dom.kernelResetButtonEl.textContent = pending ? "Reset running..." : "Kernel Reset";
      dom.kernelResetButtonEl.title = visible
        ? "Archives active Kernel runtime traces and starts the Kernel state fresh."
        : "";
    },
    renderPipelineProgress(health: HealthResponse | null, activeAgent: ChatAgentType, kernelUi: KernelUiState): void {
      pipelineDom.renderPipelineProgress(health, activeAgent, kernelUi);
    },
    renderKernelDialog(
      dialogState: KernelDialogState | null,
      statusText: string,
      pendingInteraction: KernelUiState["pendingInteraction"],
      callbacks: {
        onSubmit: (payload: Record<string, unknown>, actionLabel: string) => void;
        onCancel: (payload: { response_status: "cancelled" | "closed" | "expired"; cancellation_reason: string }, actionLabel: string) => void;
      }
    ): void {
      kernelDialogDom.render(dialogState, statusText, pendingInteraction, callbacks);
    },
    renderHealth(health: HealthResponse): void {
      if (dom.healthPillEl) {
        dom.healthPillEl.dataset.state = health.llm_ready ? "ok" : "error";
        dom.healthPillEl.textContent = health.llm_ready ? "LLM ready" : "LLM not configured";
      }
      if (dom.baseGraphPillEl) {
        const baseGraph = health.database_status?.base_graph;
        const baseGraphAvailable = Boolean(baseGraph?.available);
        const baseGraphDirty = baseGraphAvailable && Boolean(baseGraph?.dirty);
        dom.baseGraphPillEl.dataset.state = baseGraphDirty ? "warning" : baseGraphAvailable ? "ok" : "error";
        dom.baseGraphPillEl.textContent = baseGraphDirty ? "Base Graph dirty" : baseGraphAvailable ? "Base Graph ready" : "Base Graph missing";
        dom.baseGraphPillEl.title = baseGraphDirty
          ? `${Math.max(0, Number(baseGraph?.unmapped_document_count) || 0)} document(s) are not covered by the Base Graph. Refresh the Base Graph after ingestion.`
          : "";
      }
      if (dom.ontologyLensesCountEl) {
        dom.ontologyLensesCountEl.textContent = String(Math.max(0, Number(health.database_status?.ontology_lenses?.count) || 0));
      }
      if (dom.healthSummaryEl) dom.healthSummaryEl.textContent = `${health.corpus_docs} documents | model ${health.llm_model}`;
    },
    setHealthError(message: string): void {
      if (dom.healthPillEl) {
        dom.healthPillEl.dataset.state = "error";
        dom.healthPillEl.textContent = MAIN_APP_DEFAULTS.startError;
      }
      if (dom.baseGraphPillEl) {
        dom.baseGraphPillEl.dataset.state = "error";
        dom.baseGraphPillEl.textContent = "Base Graph unknown";
      }
      if (dom.ontologyLensesCountEl) dom.ontologyLensesCountEl.textContent = "0";
      if (dom.healthSummaryEl) dom.healthSummaryEl.textContent = message || MAIN_APP_DEFAULTS.healthError;
    },
    setTurnCounter(presentation: TurnCounterPresentation): void {
      if (!dom.turnCounterEl) return;
      dom.turnCounterEl.textContent = presentation.text;
      dom.turnCounterEl.title = presentation.title;
      if (presentation.state) dom.turnCounterEl.dataset.state = presentation.state;
      else delete dom.turnCounterEl.dataset.state;
    },
    setTokenCounter(presentation: TokenCounterPresentation): void {
      if (!dom.tokenCounterEl) return;
      dom.tokenCounterEl.textContent = presentation.text;
      dom.tokenCounterEl.title = presentation.title;
      if (presentation.state) dom.tokenCounterEl.dataset.state = presentation.state;
      else delete dom.tokenCounterEl.dataset.state;
    },
    setHistoryPanelHidden(hidden: boolean): void {
      if (dom.historyPanel) dom.historyPanel.hidden = hidden;
    }
  };
}

export type MainDomAdapter = ReturnType<typeof createMainDomAdapter>;
