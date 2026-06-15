import { ApiError } from "../api/client.ts";
import type { PendingChatRequest } from "../chat_controller.ts";
import type { Source } from "../types/index.ts";
import { MAIN_APP_TEXT } from "./policy.ts";
import {
  buildResetConversation,
  buildRestoredConversation,
  collectSourceCatalog,
  createAssistantMessage,
  getReferencedSources,
  mapRestoredMessages
} from "./state_domain.ts";
import { createPipelineConversationActions } from "./conversation_pipeline_workflow.ts";
import type { AppState, ChatAgentType, ChatController, ConversationMutation, MainApi } from "./types.ts";
import type { MainDomAdapter } from "./dom_adapter.ts";

function chatErrorMessage(error: unknown): string {
  return error instanceof Error ? `${MAIN_APP_TEXT.missingAnswer}: ${error.message}` : MAIN_APP_TEXT.missingAnswer;
}

function chatErrorStatus(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    return error.message;
  }
  return MAIN_APP_TEXT.sendError;
}

interface ConversationWorkflowDeps {
  api: MainApi;
  state: AppState;
  chatController: ChatController;
  domAdapter: MainDomAdapter;
  renderMessages: () => void;
  renderSources: () => void;
  renderViewer: () => void;
  applyDisplayedSources: (sources: Source[]) => void;
  refreshKernelEvents?: () => Promise<void>;
  refreshRuntimeStatus?: () => Promise<void>;
  onPipelineSubmitStart?: (message: string) => void;
  onPipelineSubmitSettled?: () => void;
}

export function createConversationWorkflow({ api, state, chatController, domAdapter, renderMessages, renderSources, renderViewer, applyDisplayedSources, refreshKernelEvents, refreshRuntimeStatus, onPipelineSubmitStart, onPipelineSubmitSettled }: ConversationWorkflowDeps) {
  let activeConversationMutation: ConversationMutation = null;
  let historyRefreshToken = 0;
  let restoreToken = 0;
  let newChatToken = 0;
  const syncInteractionState = () => domAdapter.setInteractionState(state.sending || activeConversationMutation !== null, activeConversationMutation === "newChat");
  const setSendingState = (sending: boolean) => {
    state.sending = sending;
    syncInteractionState();
  };
  const setConversationMutation = (nextMutation: ConversationMutation) => {
    activeConversationMutation = nextMutation;
    syncInteractionState();
  };
  const activeAgent = () => state.activeAgentType;
  const setStatus = (text: string, spinning = false) => domAdapter.setChatStatus(text, spinning);
  const appendMessageForAgent = (agent: ChatAgentType, message: AppState["messages"][number]) => {
    if (state.activeAgentType === agent) {
      state.messages.push(message);
      return true;
    }
    state.agentViews[agent].messages.push(message);
    return false;
  };

  const refreshHistoryList = async (): Promise<void> => {
    if (!domAdapter.dom.historyListEl) return;
    const requestToken = historyRefreshToken + 1;
    historyRefreshToken = requestToken;
    try {
      const response = await api.getChatHistory(activeAgent());
      if (requestToken === historyRefreshToken) domAdapter.renderHistoryList(response.chats);
    } catch {
      if (requestToken === historyRefreshToken) domAdapter.renderHistoryList([]);
    }
  };

  const restoreHistoryEntry = async (chatId: string): Promise<void> => {
    if (state.sending || activeConversationMutation === "newChat") return;
    const requestToken = restoreToken + 1;
    restoreToken = requestToken;
    setConversationMutation("restore");
    try {
      const result = await api.restoreChat(chatId, activeAgent());
      if (requestToken !== restoreToken) return;
      chatController.resetConversation();
      Object.assign(state, buildRestoredConversation(mapRestoredMessages(result.messages)));
      renderMessages();
      renderSources();
      renderViewer();
      domAdapter.setHistoryPanelHidden(true);
      setStatus(MAIN_APP_TEXT.restoreSuccess);
      setSendingState(chatController.isSending());
    } catch {
      if (requestToken === restoreToken) setStatus(MAIN_APP_TEXT.restoreError);
    } finally {
      if (requestToken === restoreToken && activeConversationMutation === "restore") setConversationMutation(null);
    }
  };

  const startNewChat = async (): Promise<void> => {
    if (state.sending || activeConversationMutation !== null) return;
    const requestToken = newChatToken + 1;
    newChatToken = requestToken;
    setConversationMutation("newChat");
    try {
      await api.newChat(activeAgent());
      if (requestToken !== newChatToken) return;
      chatController.resetConversation();
      Object.assign(state, buildResetConversation(activeAgent() === "pipeline" ? MAIN_APP_TEXT.pipelineWelcome : activeAgent() === "ontology" ? MAIN_APP_TEXT.ontologyWelcome : undefined));
      renderMessages();
      renderSources();
      renderViewer();
      setSendingState(chatController.isSending());
      await refreshHistoryList();
      if (requestToken === newChatToken) setStatus(MAIN_APP_TEXT.newChatSuccess);
    } catch {
      if (requestToken === newChatToken) setStatus(MAIN_APP_TEXT.newChatError);
    } finally {
      if (requestToken === newChatToken && activeConversationMutation === "newChat") setConversationMutation(null);
    }
  };

  const submitChat = async (overrideMessage = ""): Promise<void> => {
    if (state.sending || activeConversationMutation !== null) return;
    const message = overrideMessage.trim() || domAdapter.dom.chatInputEl?.value.trim();
    if (!message) return;
    const usesInputMessage = !overrideMessage.trim();
    const pendingRequest: PendingChatRequest = chatController.beginSend();
    const isPipelineTurn = activeAgent() === "pipeline";
    setSendingState(true);
    if (isPipelineTurn) onPipelineSubmitStart?.(message);
    setStatus(MAIN_APP_TEXT.thinking(state.agentName), true);
    state.messages.push({ role: "user", content: message });
    if (usesInputMessage && domAdapter.dom.chatInputEl) domAdapter.dom.chatInputEl.value = "";
    renderMessages();
    try {
      const response = await api.sendChat(message, activeAgent());
      if (!chatController.canApplyResponse(pendingRequest)) return;
      const assistantMessage = createAssistantMessage(response);
      state.messages.push(assistantMessage);
      renderMessages();
      if (activeAgent() === "pipeline" && (refreshRuntimeStatus || refreshKernelEvents)) {
        if (refreshRuntimeStatus) await refreshRuntimeStatus();
        else if (refreshKernelEvents) await refreshKernelEvents();
      }
      void refreshHistoryList();
      const referencedSources = getReferencedSources(assistantMessage, collectSourceCatalog(state.messages));
      if (referencedSources.length) {
        applyDisplayedSources(referencedSources);
        setStatus(MAIN_APP_TEXT.referencedSources(referencedSources.length));
        return;
      }
      applyDisplayedSources([]);
      setStatus(response.sources.length ? MAIN_APP_TEXT.noReferencedSources : MAIN_APP_TEXT.noNewSources);
    } catch (error) {
      if (!chatController.canApplyResponse(pendingRequest)) return;
      state.messages.push({ role: "system", content: chatErrorMessage(error) });
      renderMessages();
      setStatus(chatErrorStatus(error));
    } finally {
      chatController.finishSend(pendingRequest);
      setSendingState(chatController.isSending());
      if (isPipelineTurn) onPipelineSubmitSettled?.();
    }
  };

  const pipelineActions = createPipelineConversationActions({
    api,
    state,
    chatController,
    renderMessages,
    applyDisplayedSources,
    refreshKernelEvents,
    refreshHistoryList,
    appendMessageForAgent,
    setSendingState,
    setStatus,
    getActiveConversationMutation: () => activeConversationMutation,
    chatErrorMessage,
    chatErrorStatus,
    noReferencedSourcesText: MAIN_APP_TEXT.noReferencedSources,
    noNewSourcesText: MAIN_APP_TEXT.noNewSources,
    referencedSourcesText: MAIN_APP_TEXT.referencedSources
  });

  return {
    syncInteractionState,
    refreshHistoryList,
    restoreHistoryEntry,
    startNewChat,
    submitChat,
    submitAutomatedPipelineMessage: pipelineActions.submitAutomatedPipelineMessage,
    appendPipelineAutoResults: pipelineActions.appendPipelineAutoResults
  };
}

export type ConversationWorkflow = ReturnType<typeof createConversationWorkflow>;
