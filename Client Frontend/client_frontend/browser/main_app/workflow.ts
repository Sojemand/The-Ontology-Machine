import { getMessageRenderSources } from "../render.ts";
import { MAIN_APP_TEXT, createTokenCounterPresentation, createTurnCounterPresentation } from "./policy.ts";
import {
  cloneAppState,
  collectSourceCatalog,
  countUserTurns,
  loadConversationView,
  saveActiveConversationView,
  sumMessageTokenUsage
} from "./state_domain.ts";
import { parseDatasetIndex } from "./validation.ts";
import { createConversationWorkflow, type ConversationWorkflow } from "./conversation_workflow.ts";
import { createKernelWorkflowController } from "./workflow_kernel_controller.ts";
import { createViewerInteractions } from "./viewer_interactions.ts";
import { buildTaxonomyWorkflowCommand } from "./taxonomy_workflow_launcher.ts";
import type { AppState, ChatController, MainApi } from "./types.ts";
import type { LayoutDebugController } from "./debug.ts";
import type { MainDomAdapter } from "./dom_adapter.ts";
import type { LayoutWorkflow } from "./layout_workflow.ts";
import type { ViewerAdapter } from "./viewer_adapter.ts";

interface WorkflowDeps {
  api: MainApi;
  state: AppState;
  chatController: ChatController;
  domAdapter: MainDomAdapter;
  layoutWorkflow: LayoutWorkflow;
  viewerAdapter: ViewerAdapter;
  debug: LayoutDebugController;
  windowObject: Window;
}

export function createMainWorkflow({ api, state, chatController, domAdapter, layoutWorkflow, viewerAdapter, debug, windowObject }: WorkflowDeps) {
  const closestButton = (target: EventTarget | null, selector: string) =>
    target instanceof windowObject.Element ? (target.closest(selector) as HTMLButtonElement | null) : null;
  const renderViewer = () => viewerAdapter.render(state.viewer);
  const updateTurnCounter = () => {
    domAdapter.setTurnCounter(createTurnCounterPresentation(countUserTurns(state.messages), state.health?.memory_turns ?? 0));
    const tokenUsage = sumMessageTokenUsage(state.messages);
    domAdapter.setTokenCounter(createTokenCounterPresentation(tokenUsage.inputTokens, tokenUsage.outputTokens));
  };
  const renderMessages = () => {
    domAdapter.renderMessages(state.messages);
    updateTurnCounter();
    debug.render(state);
  };
  const renderSources = () => {
    domAdapter.renderSources(state.sources, state.viewer.selectedSource?.id || null);
    debug.render(state);
  };
  const viewer = createViewerInteractions({ state, layoutWorkflow, viewerAdapter, debug, renderSources, renderViewer });
  let conversation: ConversationWorkflow;
  const kernel = createKernelWorkflowController({
    api,
    state,
    domAdapter,
    layoutWorkflow,
    debug,
    windowObject,
    updateTurnCounter,
    appendPipelineAutoResults: (results) => conversation.appendPipelineAutoResults(results)
  });
  conversation = createConversationWorkflow({
    api,
    state,
    chatController,
    domAdapter,
    renderMessages,
    renderSources,
    renderViewer,
    applyDisplayedSources: viewer.applyDisplayedSourceSet,
    refreshKernelEvents: kernel.refreshKernelEvents,
    refreshRuntimeStatus: kernel.refreshRuntimeStatus,
    onPipelineSubmitStart: kernel.beginPipelineChatHandoff,
    onPipelineSubmitSettled: kernel.handlePipelineSubmitSettled
  });

  return {
    syncInteractionState: conversation.syncInteractionState,
    async boot(): Promise<void> {
      layoutWorkflow.refreshResponsiveLayout();
      renderMessages();
      renderSources();
      renderViewer();
      domAdapter.setActiveAgentTab(state.activeAgentType);
      kernel.renderUi();
      debug.render(state);
      void conversation.refreshHistoryList();
      await kernel.refreshHealth();
      await kernel.refreshKernelEvents();
      const isJsdom = String(windowObject.navigator?.userAgent || "").toLowerCase().includes("jsdom");
      if (!isJsdom) {
        windowObject.setInterval(() => {
          void kernel.refreshHealth();
          void kernel.refreshKernelEvents();
        }, 2500);
      }
    },
    refreshHistoryList: conversation.refreshHistoryList,
    restoreHistoryEntry: conversation.restoreHistoryEntry,
    startNewChat: conversation.startNewChat,
    async switchAgent(agentType): Promise<void> {
      if (state.sending || state.activeAgentType === agentType) return;
      saveActiveConversationView(state);
      loadConversationView(state, agentType);
      chatController.resetConversation();
      renderMessages();
      renderSources();
      renderViewer();
      domAdapter.setAgentName(state.agentName);
      domAdapter.setActiveAgentTab(state.activeAgentType);
      kernel.renderUi();
      await conversation.refreshHistoryList();
      if (agentType === "pipeline") await kernel.refreshKernelEvents();
      kernel.setAgentSwitchStatus(agentType);
    },
    selectSource: viewer.selectSource,
    cancelPipelineRun: kernel.cancelPipelineRun,
    resetKernelRuntimeState: kernel.resetKernelRuntimeState,
    refreshRuntimeStatus: kernel.refreshRuntimeStatus,
    getState(): AppState {
      return cloneAppState(state);
    },
    submitChat: conversation.submitChat,
    async startTaxonomyWorkflow(toolName: string): Promise<void> {
      if (state.activeAgentType !== "pipeline") return;
      const command = buildTaxonomyWorkflowCommand(toolName);
      if (!command) return;
      await conversation.submitChat(command);
    },
    handleMessagesClick(target: EventTarget | null): void {
      const button = closestButton(target, ".citation-button");
      const messageIndex = parseDatasetIndex(button?.dataset.messageIndex);
      const sourceIndex = parseDatasetIndex(button?.dataset.sourceIndex);
      if (messageIndex == null || sourceIndex == null) return;
      const sources = getMessageRenderSources(state.messages[messageIndex], collectSourceCatalog(state.messages));
      if (sources[sourceIndex]) viewer.selectSource(sources[sourceIndex]);
    },
    handleSourcesClick(target: EventTarget | null): void {
      const sourceIndex = parseDatasetIndex(closestButton(target, ".source-card")?.dataset.index);
      if (sourceIndex != null && state.sources[sourceIndex]) viewer.selectSource(state.sources[sourceIndex]);
    },
    handleHistoryClick(target: EventTarget | null): void {
      const chatId = closestButton(target, ".history-entry")?.dataset.chatId;
      if (chatId) void conversation.restoreHistoryEntry(chatId);
    },
    async toggleHistoryPanel(): Promise<void> {
      if (!domAdapter.dom.historyPanel) return;
      domAdapter.setHistoryPanelHidden(!domAdapter.dom.historyPanel.hidden);
      if (!domAdapter.dom.historyPanel.hidden) await conversation.refreshHistoryList();
    },
    changeViewerPage: viewer.changeViewerPage,
    applyZoom: viewer.applyZoom,
    stepZoom: viewer.stepZoom,
    canStartViewerDrag: viewer.canStartViewerDrag,
    setViewerOffsets: viewer.setViewerOffsets,
    handleViewerWheel: viewer.handleViewerWheel,
    handleViewerImageError: viewer.handleViewerImageError,
    handleViewerImageLoad: viewer.handleViewerImageLoad
  };
}

export type MainWorkflow = ReturnType<typeof createMainWorkflow>;
