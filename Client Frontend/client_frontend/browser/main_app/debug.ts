import type { AppState, DomRefs } from "./types.ts";

export function createLayoutDebugController(document: Document, windowObject: Window, dom: DomRefs) {
  const enabled = new URLSearchParams(windowObject.location.search).get("layoutdebug") === "1";
  let overlayEl: HTMLPreElement | null = null;

  function ensureOverlay(): HTMLPreElement | null {
    if (!enabled) return null;
    if (!overlayEl) {
      overlayEl = document.createElement("pre");
      overlayEl.style.cssText = [
        "position:fixed",
        "right:12px",
        "bottom:12px",
        "z-index:9999",
        "margin:0",
        "padding:10px 12px",
        "max-width:min(420px, calc(100vw - 24px))",
        "max-height:min(50vh, calc(100vh - 24px))",
        "overflow:auto",
        "border-radius:12px",
        "border:1px solid rgba(255,255,255,0.16)",
        "background:rgba(8, 10, 10, 0.88)",
        "color:#f3f2ec",
        "font:12px/1.4 Consolas, 'Courier New', monospace",
        "box-shadow:0 12px 28px rgba(0,0,0,0.35)",
        "pointer-events:none"
      ].join(";");
      document.body.appendChild(overlayEl);
    }
    return overlayEl;
  }

  function formatRect(name: string, element: Element | null | undefined): string {
    if (!element) return `${name}: missing`;
    const rect = element.getBoundingClientRect();
    return `${name}: ${Math.round(rect.width)}x${Math.round(rect.height)} @ ${Math.round(rect.left)},${Math.round(rect.top)}`;
  }

  return {
    enabled,
    render(state: AppState): void {
      const overlay = ensureOverlay();
      if (!overlay) return;
      overlay.textContent = [
        `viewport: ${windowObject.innerWidth}x${windowObject.innerHeight}`,
        `layout: ${state.layout.mode} / ${state.layout.density} / ${state.layout.activePane}`,
        `sidebar: ${Math.round(state.layout.sidebarWidth)}px`,
        `viewer: ${Math.round(state.layout.viewerWidth)}px`,
        `secondary: ${Math.round(state.layout.secondaryWidth)}px`,
        formatRect("appShell", dom.appShellEl),
        formatRect("sidebar", document.querySelector(".sidebar-panel")),
        formatRect("chat", document.querySelector(".chat-panel")),
        formatRect("viewer", document.querySelector(".viewer-panel"))
      ].join("\n");
    }
  };
}

export type LayoutDebugController = ReturnType<typeof createLayoutDebugController>;
