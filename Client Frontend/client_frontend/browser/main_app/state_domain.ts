import type { ChatResponse, ChatRestoreResponse, KernelDialogState, KernelMirrorEvent, KernelProgressEvent, Source } from "../types/index.ts";
import { collectMessageSources, getMessageReferencedSources, type UiMessage } from "../render.ts";
import { isKernelRecoveryMirror } from "./kernel_mirror_policy.ts";
import { MAIN_APP_DEFAULTS, MAIN_APP_TEXT } from "./policy.ts";
import { cloneConversationView } from "./state_clone.ts";
import type { AppState, ChatAgentType, ConversationViewState, KernelUiState, LayoutState, StoredLayoutState, ViewerState } from "./types.ts";
import { clampViewerPage, normalizeMessageRole } from "./validation.ts";

export { cloneAppState, cloneConversationView } from "./state_clone.ts";

export function createWelcomeMessage(): UiMessage {
  return { role: "system", content: MAIN_APP_DEFAULTS.welcomeMessage };
}

export function createInitialViewerState(): ViewerState {
  return { selectedSource: null, page: 1, zoom: 1, offsetX: 0, offsetY: 0, imageFailed: false };
}

export function createInitialLayoutState(stored: StoredLayoutState): LayoutState {
  return {
    mode: "wide",
    density: "comfortable",
    activePane: stored.activePane,
    sidebarWidth: stored.sidebarWidth,
    viewerWidth: stored.viewerWidth,
    secondaryWidth: stored.secondaryWidth
  };
}

export function createInitialKernelUiState(): KernelUiState {
  return {
    cursor: "",
    activeDialog: null,
    activeRecoveryEvent: null,
    latestMirrorEvent: null,
    latestProgressEvent: null,
    progressEvents: [],
    dialogStatusText: "",
    pendingInteraction: null,
    localWorkflowActivity: null,
    terminalProgressVisibleUntilMs: 0
  };
}

export function createInitialAppState(layout: LayoutState): AppState {
  const initialView = createInitialConversationView();
  return {
    customerName: MAIN_APP_DEFAULTS.customerName,
    agentName: MAIN_APP_DEFAULTS.agentName,
    activeAgentType: "query",
    queryAgentName: MAIN_APP_DEFAULTS.agentName,
    pipelineAgentName: "Taxonomy Agent",
    ontologyAgentName: "Ontology Agent",
    pipelineManager: null,
    kernelUi: createInitialKernelUiState(),
    theme: MAIN_APP_DEFAULTS.theme,
    health: null,
    messages: initialView.messages,
    sources: initialView.sources,
    viewer: initialView.viewer,
    agentViews: {
      query: cloneConversationView(initialView),
      pipeline: createInitialConversationView(MAIN_APP_TEXT.pipelineWelcome),
      ontology: createInitialConversationView(MAIN_APP_TEXT.ontologyWelcome)
    },
    layout,
    sending: false
  };
}

export function createInitialConversationView(welcome = MAIN_APP_DEFAULTS.welcomeMessage): ConversationViewState {
  return { messages: [{ role: "system", content: welcome }], sources: [], viewer: createInitialViewerState() };
}

export function saveActiveConversationView(state: AppState): void {
  state.agentViews[state.activeAgentType] = cloneConversationView({ messages: state.messages, sources: state.sources, viewer: state.viewer });
}

export function loadConversationView(state: AppState, agentType: ChatAgentType): void {
  const view = cloneConversationView(state.agentViews[agentType] || createInitialConversationView());
  state.messages = view.messages;
  state.sources = view.sources;
  state.viewer = view.viewer;
  state.activeAgentType = agentType;
  state.agentName = agentType === "pipeline" ? state.pipelineAgentName : agentType === "ontology" ? state.ontologyAgentName : state.queryAgentName;
}

export function createAssistantMessage(response: ChatResponse): UiMessage {
  return {
    role: "assistant",
    content: response.answer,
    sources: response.sources,
    mode: response.mode,
    exactness: response.exactness,
    metrics: response.metrics,
    ambiguities: response.ambiguities,
    method: response.method,
    token_usage: response.token_usage
  };
}

export function countUserTurns(messages: UiMessage[]): number {
  return messages.filter((message) => message.role === "user").length;
}

export function sumMessageTokenUsage(messages: UiMessage[]): { inputTokens: number; outputTokens: number } {
  return messages.reduce(
    (totals, message) => {
      totals.inputTokens += Math.max(0, Math.round(Number(message.token_usage?.input_tokens) || 0));
      totals.outputTokens += Math.max(0, Math.round(Number(message.token_usage?.output_tokens) || 0));
      return totals;
    },
    { inputTokens: 0, outputTokens: 0 }
  );
}

export function collectSourceCatalog(messages: UiMessage[]): Source[] {
  return collectMessageSources(messages);
}

export function getReferencedSources(message: UiMessage | undefined, catalog: Source[]): Source[] {
  return getMessageReferencedSources(message, catalog);
}

export function mapRestoredMessages(messages: ChatRestoreResponse["messages"]): UiMessage[] {
  return messages.map((message) => ({
    role: normalizeMessageRole(message.role),
    content: message.content,
    sources: message.sources,
    mode: message.mode,
    exactness: message.exactness,
    metrics: message.metrics,
    ambiguities: message.ambiguities,
    method: message.method,
    token_usage: message.token_usage
  }));
}

export function extractLatestAssistantSources(messages: UiMessage[]): Source[] {
  const catalog = collectSourceCatalog(messages);
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const referencedSources = getReferencedSources(messages[index], catalog);
    if (referencedSources.length) return referencedSources;
  }
  return [];
}

export function selectSourceViewer(source: Source): ViewerState {
  return { selectedSource: source, page: source.page || 1, zoom: 1, offsetX: 0, offsetY: 0, imageFailed: false };
}

export function applyDisplayedSources(viewer: ViewerState, sources: Source[]): { sources: Source[]; viewer: ViewerState } {
  const selectedSourceId = viewer.selectedSource?.id || null;
  const matchingSelection = selectedSourceId ? sources.find((source) => source.id === selectedSourceId) || null : null;
  if (matchingSelection) {
    return {
      sources,
      viewer: {
        ...viewer,
        selectedSource: matchingSelection,
        page: clampViewerPage(viewer.page, matchingSelection.page_count || 1),
        imageFailed: false
      }
    };
  }
  if (sources[0]) return { sources, viewer: selectSourceViewer(sources[0]) };
  return { sources: [], viewer: createInitialViewerState() };
}

export function buildResetConversation(welcome = MAIN_APP_DEFAULTS.welcomeMessage): Pick<AppState, "messages" | "sources" | "viewer"> {
  return { messages: [{ role: "system", content: welcome }], sources: [], viewer: createInitialViewerState() };
}

export function buildRestoredConversation(messages: UiMessage[]): Pick<AppState, "messages" | "sources" | "viewer"> {
  return {
    messages: [createWelcomeMessage(), ...messages],
    sources: extractLatestAssistantSources(messages),
    viewer: createInitialViewerState()
  };
}

export function applyKernelDialogState(state: AppState, dialog: KernelDialogState | null, statusText = ""): void {
  state.kernelUi.activeDialog = dialog;
  state.kernelUi.dialogStatusText = statusText;
}

export function applyKernelMirrorState(state: AppState, mirrorEvent: KernelMirrorEvent | null): void {
  state.kernelUi.latestMirrorEvent = mirrorEvent;
  if (!mirrorEvent) return;
  if (isKernelRecoveryMirror(mirrorEvent)) {
    state.kernelUi.activeRecoveryEvent = mirrorEvent;
  }
}

export function applyKernelProgressState(state: AppState, progressEvent: KernelProgressEvent | null): void {
  state.kernelUi.latestProgressEvent = progressEvent;
  if (!progressEvent) return;
  const withoutSameStep = state.kernelUi.progressEvents.filter((event) => {
    return !(event.workflow_run_id === progressEvent.workflow_run_id && event.step_id === progressEvent.step_id);
  });
  state.kernelUi.progressEvents = [...withoutSameStep, progressEvent].sort((left, right) => {
    if (left.workflow_run_id !== right.workflow_run_id) return String(left.workflow_run_id).localeCompare(String(right.workflow_run_id));
    return Number(left.sequence_index || 0) - Number(right.sequence_index || 0);
  });
}
