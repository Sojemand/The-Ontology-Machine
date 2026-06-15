import type { PendingChatRequest } from "../chat_controller.ts";
import type {
  ChatHistoryResponse,
  ChatResponse,
  ChatRestoreResponse,
  HealthResponse,
  KernelClientFrontendEventBatch,
  KernelDialogState,
  KernelInteractionRouteResponse,
  KernelMirrorEvent,
  KernelProgressEvent,
  KernelRuntimeResetResponse,
  KernelUserInteractionResponse,
  PipelineManagerState,
  PipelineRunCancelResponse,
  Source
} from "../types/index.ts";
import type { UiMessage, UiMessageRole } from "../render.ts";

export type MessageRole = UiMessageRole;
export type ChatAgentType = "query" | "pipeline" | "ontology";
export type LayoutMode = "wide" | "laptop" | "compact";
export type LayoutDensity = "comfortable" | "compact" | "dense";
export type WorkspacePane = "sources" | "chat" | "viewer";
export type ConversationMutation = "restore" | "newChat" | null;
export type Theme = "dark" | "light";
export type ResizerSide = "left" | "right";
export type TurnCounterState = "warning" | "over" | null;
export type TokenCounterState = "warning" | "over" | null;

export interface ViewerState {
  selectedSource: Source | null;
  page: number;
  zoom: number;
  offsetX: number;
  offsetY: number;
  imageFailed: boolean;
}

export interface LayoutState {
  mode: LayoutMode;
  density: LayoutDensity;
  activePane: WorkspacePane;
  sidebarWidth: number;
  viewerWidth: number;
  secondaryWidth: number;
}

export interface KernelUiState {
  cursor: string;
  activeDialog: KernelDialogState | null;
  activeRecoveryEvent: KernelMirrorEvent | null;
  latestMirrorEvent: KernelMirrorEvent | null;
  latestProgressEvent: KernelProgressEvent | null;
  progressEvents: KernelProgressEvent[];
  dialogStatusText: string;
  pendingInteraction: KernelPendingInteractionState | null;
  localWorkflowActivity: KernelLocalWorkflowActivity | null;
  terminalProgressVisibleUntilMs: number;
}

export interface KernelPendingInteractionState {
  requestId: string;
  actionLabel: string;
  statusText: string;
  submittedAt: string;
}

export interface KernelLocalWorkflowActivity {
  activityId: string;
  title: string;
  summary: string;
  state: "running" | "waiting";
  workflowRunId?: string;
  workflowTool?: string;
  startedAtMs: number;
  expiresAtMs?: number;
}

export interface AppState {
  customerName: string;
  agentName: string;
  activeAgentType: ChatAgentType;
  queryAgentName: string;
  pipelineAgentName: string;
  ontologyAgentName: string;
  pipelineManager: PipelineManagerState | null;
  kernelUi: KernelUiState;
  theme: Theme;
  health: HealthResponse | null;
  messages: UiMessage[];
  sources: Source[];
  viewer: ViewerState;
  agentViews: Record<ChatAgentType, ConversationViewState>;
  layout: LayoutState;
  sending: boolean;
}

export interface ConversationViewState {
  messages: UiMessage[];
  sources: Source[];
  viewer: ViewerState;
}

export interface StoredLayoutState {
  activePane: WorkspacePane;
  sidebarWidth: number;
  viewerWidth: number;
  secondaryWidth: number;
}

export interface TurnCounterPresentation {
  text: string;
  title: string;
  state: TurnCounterState;
}

export interface TokenCounterPresentation {
  text: string;
  title: string;
  state: TokenCounterState;
}

export interface MainApi {
  getChatHistory: (agent?: ChatAgentType) => Promise<ChatHistoryResponse>;
  getHealth: () => Promise<HealthResponse>;
  newChat: (agent?: ChatAgentType) => Promise<unknown>;
  restoreChat: (chatId: string, agent?: ChatAgentType) => Promise<ChatRestoreResponse>;
  sendChat: (message: string, agent?: ChatAgentType) => Promise<ChatResponse>;
  cancelPipelineRun: (runId?: string) => Promise<PipelineRunCancelResponse>;
  resetKernelRuntimeState: () => Promise<KernelRuntimeResetResponse>;
  getPipelineKernelEvents: (after?: string) => Promise<KernelClientFrontendEventBatch>;
  submitKernelInteractionResponse: (interactionRequestId: string, payload: KernelUserInteractionResponse) => Promise<KernelInteractionRouteResponse>;
  cancelKernelInteraction: (interactionRequestId: string, payload: KernelUserInteractionResponse) => Promise<KernelInteractionRouteResponse>;
}

export interface ChatController {
  beginSend(): PendingChatRequest;
  resetConversation(): number;
  canApplyResponse(request: PendingChatRequest | null | undefined): boolean;
  finishSend(request: PendingChatRequest | null | undefined): void;
  isSending(): boolean;
}

export interface MainAppOptions {
  api?: MainApi;
  document?: Document;
  window?: Window;
  createChatControllerFn?: () => ChatController;
}

export interface MainApp {
  boot(): Promise<void>;
  refreshHistoryList(): Promise<void>;
  restoreHistoryEntry(chatId: string): Promise<void>;
  startNewChat(): Promise<void>;
  switchAgent(agent: ChatAgentType): Promise<void>;
  refreshRuntimeStatus(): Promise<void>;
  selectSource(source: Source): void;
  getState(): AppState;
}

export interface DomRefs {
  appFrameEl: HTMLDivElement | null;
  appShellEl: HTMLDivElement | null;
  workspaceNavEl: HTMLElement | null;
  workspaceNavButtons: HTMLButtonElement[];
  leftResizerEl: HTMLDivElement | null;
  rightResizerEl: HTMLDivElement | null;
  customerNameEl: HTMLHeadingElement | null;
  agentNameEl: HTMLHeadingElement | null;
  agentTabs: HTMLButtonElement[];
  pipelinePermissionEl: HTMLParagraphElement | null;
  pipelineProgressPanelEl: HTMLElement | null;
  pipelineProgressTitleEl: HTMLHeadingElement | null;
  pipelineProgressCountEl: HTMLSpanElement | null;
  pipelineAbortButtonEl: HTMLButtonElement | null;
  kernelResetButtonEl: HTMLButtonElement | null;
  pipelineProgressFillEl: HTMLSpanElement | null;
  pipelineProgressSummaryEl: HTMLParagraphElement | null;
  pipelineStageListEl: HTMLDivElement | null;
  kernelDialogPanelEl: HTMLElement | null;
  kernelDialogTitleEl: HTMLHeadingElement | null;
  kernelDialogSummaryEl: HTMLParagraphElement | null;
  kernelDialogBodyEl: HTMLDivElement | null;
  kernelDialogActionsEl: HTMLDivElement | null;
  kernelDialogStatusEl: HTMLParagraphElement | null;
  themeToggleEl: HTMLButtonElement | null;
  healthPillEl: HTMLSpanElement | null;
  baseGraphPillEl: HTMLSpanElement | null;
  ontologyLensesCountEl: HTMLSpanElement | null;
  healthSummaryEl: HTMLParagraphElement | null;
  sourceCountEl: HTMLSpanElement | null;
  sourcesListEl: HTMLDivElement | null;
  messagesEl: HTMLDivElement | null;
  chatFormEl: HTMLFormElement | null;
  chatInputEl: HTMLTextAreaElement | null;
  taxonomyWorkflowLauncherEl: HTMLDivElement | null;
  taxonomyWorkflowMenuButtonEl: HTMLButtonElement | null;
  taxonomyWorkflowMenuListEl: HTMLDivElement | null;
  chatStatusEl: HTMLParagraphElement | null;
  sendButtonEl: HTMLButtonElement | null;
  viewerTitleEl: HTMLHeadingElement | null;
  viewerMetaEl: HTMLDivElement | null;
  viewerStageEl: HTMLDivElement | null;
  viewerPlaceholderEl: HTMLDivElement | null;
  pageLabelEl: HTMLSpanElement | null;
  pagePrevEl: HTMLButtonElement | null;
  pageNextEl: HTMLButtonElement | null;
  zoomInEl: HTMLButtonElement | null;
  zoomOutEl: HTMLButtonElement | null;
  zoomResetEl: HTMLButtonElement | null;
  turnCounterEl: HTMLSpanElement | null;
  tokenCounterEl: HTMLSpanElement | null;
  newChatBtn: HTMLButtonElement | null;
  historyBtn: HTMLButtonElement | null;
  historyPanel: HTMLDivElement | null;
  historyListEl: HTMLDivElement | null;
  historyCloseBtn: HTMLButtonElement | null;
}
