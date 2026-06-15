import {
  cancelKernelInteraction,
  cancelPipelineRun,
  getChatHistory,
  getHealth,
  getPipelineKernelEvents,
  newChat,
  resetKernelRuntimeState,
  restoreChat,
  sendChat,
  submitKernelInteractionResponse
} from "../api/client.ts";
import { createChatController } from "../chat_controller.ts";
import { STORAGE_KEYS, VIEWER_LIMITS } from "./policy.ts";
import { createInitialAppState, createInitialLayoutState } from "./state_domain.ts";
import { createLayoutDebugController } from "./debug.ts";
import { createMainDomAdapter } from "./dom_adapter.ts";
import { createLayoutWorkflow } from "./layout_workflow.ts";
import type { MainApi, MainApp, MainAppOptions, StoredLayoutState } from "./types.ts";
import { TAXONOMY_WORKFLOW_OPTIONS } from "./taxonomy_workflow_launcher.ts";
import { createViewerAdapter } from "./viewer_adapter.ts";
import { createMainWorkflow } from "./workflow.ts";

const DEFAULT_API: MainApi = {
  cancelPipelineRun,
  getChatHistory,
  getHealth,
  getPipelineKernelEvents,
  newChat,
  restoreChat,
  sendChat,
  resetKernelRuntimeState,
  submitKernelInteractionResponse,
  cancelKernelInteraction
};

function bindResizer(element: HTMLDivElement | null, resizer: "left" | "right", workflow: ReturnType<typeof createLayoutWorkflow>): void {
  if (!element) return;
  let activePointerId: number | null = null;
  element.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    activePointerId = event.pointerId;
    element.setPointerCapture(event.pointerId);
    workflow.resizePaneFromPointer(resizer, event.clientX);
    event.preventDefault();
  });
  element.addEventListener("pointermove", (event) => {
    if (activePointerId === event.pointerId) workflow.resizePaneFromPointer(resizer, event.clientX);
  });
  const stopResize = (event: PointerEvent) => {
    if (activePointerId === event.pointerId) activePointerId = null;
  };
  element.addEventListener("pointerup", stopResize);
  element.addEventListener("pointercancel", stopResize);
  element.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    workflow.stepPaneSize(resizer, event.key === "ArrowLeft" ? -24 : 24);
    event.preventDefault();
  });
}

export function createMainApp(options: MainAppOptions = {}): MainApp {
  const windowObject = options.window ?? globalThis.window;
  const document = options.document ?? windowObject.document;
  const domAdapter = createMainDomAdapter(document, windowObject);
  const storedLayout: StoredLayoutState = {
    activePane: domAdapter.readStoredPane(),
    sidebarWidth: domAdapter.readStoredNumber(STORAGE_KEYS.sidebarWidth, 304),
    viewerWidth: domAdapter.readStoredNumber(STORAGE_KEYS.viewerWidth, 336),
    secondaryWidth: domAdapter.readStoredNumber(STORAGE_KEYS.secondaryWidth, 320)
  };
  const state = createInitialAppState(createInitialLayoutState(storedLayout));
  const storedTheme = domAdapter.readStoredTheme();
  if (storedTheme) state.theme = storedTheme;
  const debug = createLayoutDebugController(document, windowObject, domAdapter.dom);
  const layoutWorkflow = createLayoutWorkflow({ state, domAdapter, debug });
  let workflow: ReturnType<typeof createMainWorkflow>;
  const viewerAdapter = createViewerAdapter({
    document,
    dom: domAdapter.dom,
    onImageError: () => workflow.handleViewerImageError(),
    onImageLoad: () => workflow.handleViewerImageLoad(),
    onDebugRefresh: () => debug.render(state)
  });
  workflow = createMainWorkflow({
    api: options.api ?? DEFAULT_API,
    state,
    chatController: (options.createChatControllerFn ?? createChatController)(),
    domAdapter,
    layoutWorkflow,
    viewerAdapter,
    debug,
    windowObject
  });
  domAdapter.renderTaxonomyWorkflowOptions(TAXONOMY_WORKFLOW_OPTIONS);

  domAdapter.dom.chatFormEl?.addEventListener("submit", (event) => {
    event.preventDefault();
    void workflow.submitChat();
  });
  domAdapter.dom.taxonomyWorkflowMenuButtonEl?.addEventListener("click", (event) => {
    event.stopPropagation();
    domAdapter.toggleTaxonomyWorkflowMenu();
  });
  domAdapter.dom.taxonomyWorkflowMenuListEl?.addEventListener("click", (event) => {
    const target = event.target;
    const button = target instanceof windowObject.Element ? target.closest(".taxonomy-workflow-option") as HTMLButtonElement | null : null;
    const toolName = button?.dataset.toolName || "";
    domAdapter.setTaxonomyWorkflowMenuOpen(false);
    void workflow.startTaxonomyWorkflow(toolName);
  });
  document.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof windowObject.Node && domAdapter.dom.taxonomyWorkflowLauncherEl?.contains(target)) return;
    domAdapter.setTaxonomyWorkflowMenuOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") domAdapter.setTaxonomyWorkflowMenuOpen(false);
  });
  domAdapter.dom.chatInputEl?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      domAdapter.dom.chatFormEl?.requestSubmit();
    }
  });
  domAdapter.dom.themeToggleEl?.addEventListener("click", () => layoutWorkflow.toggleTheme());
  domAdapter.dom.messagesEl?.addEventListener("click", (event) => workflow.handleMessagesClick(event.target));
  domAdapter.dom.sourcesListEl?.addEventListener("click", (event) => workflow.handleSourcesClick(event.target));
  domAdapter.dom.historyListEl?.addEventListener("click", (event) => workflow.handleHistoryClick(event.target));
  domAdapter.dom.newChatBtn?.addEventListener("click", () => void workflow.startNewChat());
  domAdapter.dom.historyBtn?.addEventListener("click", () => void workflow.toggleHistoryPanel());
  domAdapter.dom.historyCloseBtn?.addEventListener("click", () => domAdapter.setHistoryPanelHidden(true));
  domAdapter.dom.pipelineAbortButtonEl?.addEventListener("click", () => void workflow.cancelPipelineRun());
  domAdapter.dom.kernelResetButtonEl?.addEventListener("click", () => void workflow.resetKernelRuntimeState());
  domAdapter.dom.pagePrevEl?.addEventListener("click", () => workflow.changeViewerPage(-1));
  domAdapter.dom.pageNextEl?.addEventListener("click", () => workflow.changeViewerPage(1));
  domAdapter.dom.zoomInEl?.addEventListener("click", () => workflow.stepZoom(VIEWER_LIMITS.buttonStep));
  domAdapter.dom.zoomOutEl?.addEventListener("click", () => workflow.stepZoom(-VIEWER_LIMITS.buttonStep));
  domAdapter.dom.zoomResetEl?.addEventListener("click", () => workflow.applyZoom(1));
  windowObject.addEventListener("resize", () => layoutWorkflow.refreshResponsiveLayout());
  domAdapter.dom.workspaceNavButtons.forEach((button) =>
    button.addEventListener("click", () => {
      const pane = button.dataset.pane;
      if (pane === "sources" || pane === "chat" || pane === "viewer") layoutWorkflow.setActiveWorkspacePane(pane);
    })
  );
  domAdapter.dom.agentTabs.forEach((button) =>
    button.addEventListener("click", () => {
      const agent = button.dataset.agent;
      if (agent === "query" || agent === "pipeline" || agent === "ontology") void workflow.switchAgent(agent);
    })
  );
  bindResizer(domAdapter.dom.leftResizerEl, "left", layoutWorkflow);
  bindResizer(domAdapter.dom.rightResizerEl, "right", layoutWorkflow);

  let dragOrigin: { x: number; y: number } | null = null;
  domAdapter.dom.viewerStageEl?.addEventListener("pointerdown", (event) => {
    if (!workflow.canStartViewerDrag(event.button)) return;
    dragOrigin = { x: event.clientX - state.viewer.offsetX, y: event.clientY - state.viewer.offsetY };
    domAdapter.dom.viewerStageEl?.setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  domAdapter.dom.viewerStageEl?.addEventListener("pointermove", (event) => {
    if (dragOrigin) workflow.setViewerOffsets(event.clientX - dragOrigin.x, event.clientY - dragOrigin.y);
  });
  domAdapter.dom.viewerStageEl?.addEventListener("pointerup", () => {
    dragOrigin = null;
  });
  domAdapter.dom.viewerStageEl?.addEventListener("pointercancel", () => {
    dragOrigin = null;
  });
  domAdapter.dom.viewerStageEl?.addEventListener("wheel", (event) => {
    if (!domAdapter.dom.viewerStageEl) return;
    event.preventDefault();
    workflow.handleViewerWheel(event.deltaY, event.clientX, event.clientY, domAdapter.dom.viewerStageEl.getBoundingClientRect());
  });

  workflow.syncInteractionState();
  if (debug.enabled) windowObject.setInterval(() => debug.render(state), 1000);
  return {
    boot: workflow.boot,
    refreshHistoryList: workflow.refreshHistoryList,
    restoreHistoryEntry: workflow.restoreHistoryEntry,
    startNewChat: workflow.startNewChat,
    switchAgent: workflow.switchAgent,
    refreshRuntimeStatus: workflow.refreshRuntimeStatus,
    selectSource: workflow.selectSource,
    getState: workflow.getState
  };
}
