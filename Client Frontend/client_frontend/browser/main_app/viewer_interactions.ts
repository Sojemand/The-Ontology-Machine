import { VIEWER_LIMITS } from "./policy.ts";
import { applyDisplayedSources, selectSourceViewer } from "./state_domain.ts";
import type { LayoutDebugController } from "./debug.ts";
import type { LayoutWorkflow } from "./layout_workflow.ts";
import type { AppState, Source } from "./types.ts";
import { clampViewerPage, clampViewerZoom } from "./validation.ts";
import type { ViewerAdapter } from "./viewer_adapter.ts";

interface ViewerInteractionDeps {
  state: AppState;
  layoutWorkflow: LayoutWorkflow;
  viewerAdapter: ViewerAdapter;
  debug: LayoutDebugController;
  renderSources: () => void;
  renderViewer: () => void;
}

export function createViewerInteractions({ state, layoutWorkflow, viewerAdapter, debug, renderSources, renderViewer }: ViewerInteractionDeps) {
  const applyZoom = (nextZoom: number): void => {
    state.viewer.zoom = clampViewerZoom(nextZoom);
    if (state.viewer.zoom === 1) {
      state.viewer.offsetX = 0;
      state.viewer.offsetY = 0;
    }
    viewerAdapter.updateTransform(state.viewer);
  };
  return {
    applyDisplayedSourceSet(sources: Source[]): void {
      const next = applyDisplayedSources(state.viewer, sources);
      state.sources = next.sources;
      state.viewer = next.viewer;
      renderSources();
      renderViewer();
    },
    selectSource(source: Source): void {
      state.viewer = selectSourceViewer(source);
      renderSources();
      renderViewer();
      if (state.layout.mode !== "wide") layoutWorkflow.setActiveWorkspacePane("viewer");
    },
    changeViewerPage(delta: number): void {
      const nextPage = clampViewerPage(state.viewer.page + delta, state.viewer.selectedSource?.page_count || 1);
      if (nextPage === state.viewer.page) return;
      state.viewer.page = nextPage;
      state.viewer.imageFailed = false;
      renderViewer();
    },
    applyZoom,
    stepZoom(delta: number): void {
      const nextZoom = clampViewerZoom(state.viewer.zoom + delta);
      if (nextZoom !== state.viewer.zoom) applyZoom(nextZoom);
    },
    canStartViewerDrag(button: number): boolean {
      return button === 0 && state.viewer.zoom > 1 && Boolean(state.viewer.selectedSource);
    },
    setViewerOffsets(offsetX: number, offsetY: number): void {
      state.viewer.offsetX = offsetX;
      state.viewer.offsetY = offsetY;
      viewerAdapter.updateTransform(state.viewer);
    },
    handleViewerWheel(deltaY: number, clientX: number, clientY: number, rect: DOMRect): void {
      if (!state.viewer.selectedSource) return;
      const oldZoom = state.viewer.zoom;
      const nextZoom = clampViewerZoom(oldZoom + (deltaY < 0 ? VIEWER_LIMITS.wheelStep : -VIEWER_LIMITS.wheelStep));
      if (nextZoom === oldZoom) return;
      const cursorX = clientX - rect.left - rect.width / 2;
      const cursorY = clientY - rect.top - rect.height / 2;
      const ratio = nextZoom / oldZoom;
      state.viewer.offsetX = cursorX - (cursorX - state.viewer.offsetX) * ratio;
      state.viewer.offsetY = cursorY - (cursorY - state.viewer.offsetY) * ratio;
      state.viewer.zoom = nextZoom;
      if (nextZoom === 1) {
        state.viewer.offsetX = 0;
        state.viewer.offsetY = 0;
      }
      viewerAdapter.updateTransform(state.viewer);
    },
    handleViewerImageError(): void {
      state.viewer.imageFailed = true;
      renderViewer();
    },
    handleViewerImageLoad(): void {
      if (state.viewer.imageFailed) {
        state.viewer.imageFailed = false;
        renderViewer();
        return;
      }
      debug.render(state);
    }
  };
}
