import { LAYOUT_LIMITS, STORAGE_KEYS, clamp, clampLayoutState, resolveLayoutDensity, resolveLayoutMode } from "./policy.ts";
import type { AppState, ResizerSide, Theme, WorkspacePane } from "./types.ts";
import type { LayoutDebugController } from "./debug.ts";
import type { MainDomAdapter } from "./dom_adapter.ts";

interface LayoutWorkflowDeps {
  state: AppState;
  domAdapter: MainDomAdapter;
  debug: LayoutDebugController;
}

export function createLayoutWorkflow({ state, domAdapter, debug }: LayoutWorkflowDeps) {
  const getShellWidth = () => domAdapter.dom.appShellEl?.clientWidth || Math.max(960, domAdapter.windowObject.innerWidth - 24);

  const syncWorkspaceNav = () => {
    const isWide = state.layout.mode === "wide";
    if (domAdapter.dom.workspaceNavEl) domAdapter.dom.workspaceNavEl.hidden = isWide;
    domAdapter.dom.workspaceNavButtons.forEach((button) => {
      const pane = button.dataset.pane as WorkspacePane | undefined;
      button.setAttribute("aria-pressed", String(pane === state.layout.activePane));
      button.title =
        state.layout.mode !== "laptop"
          ? ""
          : pane === "chat"
            ? "Show chat only"
            : pane === "sources"
              ? "Show chat and sources"
              : "Show chat and document";
    });
  };

  const applyLayoutState = () => {
    state.layout = clampLayoutState(state.layout, getShellWidth());
    domAdapter.document.body.dataset.density = state.layout.density;
    if (domAdapter.dom.appFrameEl) {
      domAdapter.dom.appFrameEl.dataset.layout = state.layout.mode;
      domAdapter.dom.appFrameEl.dataset.activePane = state.layout.activePane;
      domAdapter.dom.appFrameEl.dataset.density = state.layout.density;
    }
    if (domAdapter.dom.appShellEl) {
      domAdapter.dom.appShellEl.style.setProperty("--sidebar-width", `${Math.round(state.layout.sidebarWidth)}px`);
      domAdapter.dom.appShellEl.style.setProperty("--viewer-width", `${Math.round(state.layout.viewerWidth)}px`);
      domAdapter.dom.appShellEl.style.setProperty("--secondary-width", `${Math.round(state.layout.secondaryWidth)}px`);
      domAdapter.dom.appShellEl.style.setProperty("--resizer-size", `${LAYOUT_LIMITS.resizer}px`);
    }
    if (domAdapter.dom.leftResizerEl) domAdapter.dom.leftResizerEl.hidden = state.layout.mode !== "wide";
    if (domAdapter.dom.rightResizerEl) domAdapter.dom.rightResizerEl.hidden = state.layout.mode === "compact";
    syncWorkspaceNav();
    domAdapter.fitCustomerName(state.layout.density);
    debug.render(state);
  };

  const applyTheme = (theme: Theme, { persist = false }: { persist?: boolean } = {}) => {
    state.theme = theme;
    if (persist) domAdapter.writeStoredTheme(theme);
    domAdapter.setTheme(theme);
    debug.render(state);
  };

  return {
    applyLayoutState,
    applyTheme,
    toggleTheme(): void {
      applyTheme(state.theme === "dark" ? "light" : "dark", { persist: true });
    },
    refreshResponsiveLayout(): void {
      state.layout.mode = resolveLayoutMode(domAdapter.windowObject.innerWidth, domAdapter.windowObject.innerHeight);
      state.layout.density = resolveLayoutDensity(domAdapter.windowObject.innerWidth, domAdapter.windowObject.innerHeight);
      applyLayoutState();
    },
    setActiveWorkspacePane(nextPane: WorkspacePane, { persist = true }: { persist?: boolean } = {}): void {
      state.layout.activePane = nextPane;
      if (persist) domAdapter.writeStoredPane(nextPane);
      applyLayoutState();
    },
    resizePaneFromPointer(resizer: ResizerSide, clientX: number): void {
      const shellRect = domAdapter.dom.appShellEl?.getBoundingClientRect();
      if (!shellRect) return;
      if (state.layout.mode === "wide") {
        const maxWidth =
          resizer === "left"
            ? Math.min(LAYOUT_LIMITS.sidebar.max, shellRect.width - LAYOUT_LIMITS.resizer * 2 - LAYOUT_LIMITS.chat.min - LAYOUT_LIMITS.viewer.min)
            : Math.min(LAYOUT_LIMITS.viewer.max, shellRect.width - LAYOUT_LIMITS.resizer * 2 - LAYOUT_LIMITS.chat.min - LAYOUT_LIMITS.sidebar.min);
        if (resizer === "left") {
          state.layout.sidebarWidth = clamp(clientX - shellRect.left, LAYOUT_LIMITS.sidebar.min, Math.max(LAYOUT_LIMITS.sidebar.min, maxWidth));
          domAdapter.writeStoredNumber(STORAGE_KEYS.sidebarWidth, state.layout.sidebarWidth);
        } else {
          state.layout.viewerWidth = clamp(shellRect.right - clientX, LAYOUT_LIMITS.viewer.min, Math.max(LAYOUT_LIMITS.viewer.min, maxWidth));
          domAdapter.writeStoredNumber(STORAGE_KEYS.viewerWidth, state.layout.viewerWidth);
        }
        return applyLayoutState();
      }
      if (state.layout.mode === "laptop" && resizer === "right" && state.layout.activePane !== "chat") {
        const maxWidth = Math.min(LAYOUT_LIMITS.secondary.max, shellRect.width - LAYOUT_LIMITS.resizer - LAYOUT_LIMITS.chat.min);
        state.layout.secondaryWidth = clamp(shellRect.right - clientX, LAYOUT_LIMITS.secondary.min, Math.max(LAYOUT_LIMITS.secondary.min, maxWidth));
        domAdapter.writeStoredNumber(STORAGE_KEYS.secondaryWidth, state.layout.secondaryWidth);
        applyLayoutState();
      }
    },
    stepPaneSize(resizer: ResizerSide, delta: number): void {
      if (state.layout.mode === "wide") {
        if (resizer === "left") {
          state.layout.sidebarWidth += delta;
          domAdapter.writeStoredNumber(STORAGE_KEYS.sidebarWidth, state.layout.sidebarWidth);
        } else {
          state.layout.viewerWidth -= delta;
          domAdapter.writeStoredNumber(STORAGE_KEYS.viewerWidth, state.layout.viewerWidth);
        }
        return applyLayoutState();
      }
      if (state.layout.mode === "laptop" && resizer === "right" && state.layout.activePane !== "chat") {
        state.layout.secondaryWidth -= delta;
        domAdapter.writeStoredNumber(STORAGE_KEYS.secondaryWidth, state.layout.secondaryWidth);
        applyLayoutState();
      }
    }
  };
}

export type LayoutWorkflow = ReturnType<typeof createLayoutWorkflow>;
