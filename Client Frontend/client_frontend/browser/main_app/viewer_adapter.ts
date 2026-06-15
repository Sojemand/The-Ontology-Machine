import { buildViewerPresentation } from "../render.ts";
import type { DomRefs, ViewerState } from "./types.ts";

interface ViewerAdapterDeps {
  document: Document;
  dom: DomRefs;
  onImageError: () => void;
  onImageLoad: () => void;
  onDebugRefresh: () => void;
}

export function createViewerAdapter({ document, dom, onImageError, onImageLoad, onDebugRefresh }: ViewerAdapterDeps) {
  let viewerImageEl = document.querySelector<HTMLImageElement>("#viewer-image");
  let viewerImageToken = 0;
  let viewerRequestedSrc: string | null = null;

  const invalidateRequest = () => {
    viewerImageToken += 1;
    viewerRequestedSrc = null;
  };
  const replaceImageNode = () => {
    if (!viewerImageEl) return null;
    const nextImageEl = viewerImageEl.cloneNode(false) as HTMLImageElement;
    viewerImageEl.replaceWith(nextImageEl);
    viewerImageEl = nextImageEl;
    return nextImageEl;
  };

  const updateTransform = (viewer: ViewerState) => {
    if (!viewerImageEl || !dom.zoomResetEl) return;
    viewerImageEl.style.transform = `translate(${viewer.offsetX}px, ${viewer.offsetY}px) scale(${viewer.zoom})`;
    dom.zoomResetEl.textContent = `${Math.round(viewer.zoom * 100)}%`;
  };

  function ensureImage(src: string, viewer: ViewerState): void {
    if (!viewerImageEl || !dom.viewerPlaceholderEl) return;
    if (viewerRequestedSrc === src && viewerImageEl.getAttribute("src") === src) {
      viewerImageEl.hidden = false;
      dom.viewerPlaceholderEl.hidden = true;
      updateTransform(viewer);
      return;
    }

    const requestToken = viewerImageToken + 1;
    viewerImageToken = requestToken;
    viewerRequestedSrc = src;
    const imageEl = replaceImageNode();
    if (!imageEl) return;

    imageEl.addEventListener("error", () => {
      if (requestToken === viewerImageToken && viewerRequestedSrc === src) onImageError();
    });
    imageEl.addEventListener("load", () => {
      if (requestToken === viewerImageToken && viewerRequestedSrc === src) onImageLoad();
    });
    imageEl.hidden = false;
    dom.viewerPlaceholderEl.hidden = true;
    imageEl.src = src;
    updateTransform(viewer);
  }

  return {
    updateTransform,
    render(viewer: ViewerState): void {
      if (!dom.viewerTitleEl || !dom.viewerMetaEl || !dom.pageLabelEl || !dom.viewerPlaceholderEl || !viewerImageEl) return;
      const presentation = buildViewerPresentation(viewer);
      dom.viewerTitleEl.textContent = presentation.title;
      dom.viewerMetaEl.textContent = presentation.meta;
      dom.pageLabelEl.textContent = presentation.pageLabel;
      if (dom.pagePrevEl) dom.pagePrevEl.disabled = presentation.disablePrev;
      if (dom.pageNextEl) dom.pageNextEl.disabled = presentation.disableNext;
      if (presentation.imageSrc) return ensureImage(presentation.imageSrc, viewer);
      invalidateRequest();
      viewerImageEl.hidden = true;
      viewerImageEl.removeAttribute("src");
      dom.viewerPlaceholderEl.hidden = false;
      dom.viewerPlaceholderEl.textContent = presentation.placeholderText || "";
      onDebugRefresh();
    }
  };
}

export type ViewerAdapter = ReturnType<typeof createViewerAdapter>;
