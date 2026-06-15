import type { LayoutDensity, LayoutMode, LayoutState, Theme, TokenCounterPresentation, TurnCounterPresentation } from "./types.ts";

export const STORAGE_KEYS = {
  sidebarWidth: "vp-layout-sidebar-width",
  viewerWidth: "vp-layout-viewer-width",
  secondaryWidth: "vp-layout-secondary-width",
  activePane: "vp-layout-active-pane",
  theme: "vp-main-theme"
} as const;

export const LAYOUT_LIMITS = {
  sidebar: { min: 220, max: 460 },
  chat: { min: 320 },
  viewer: { min: 240, max: 520 },
  secondary: { min: 240, max: 460 },
  resizer: 14
} as const;

export const VIEWER_LIMITS = {
  zoomMin: 1,
  zoomMax: 4.5,
  buttonStep: 0.2,
  wheelStep: 0.15
} as const;

export const MAIN_APP_DEFAULTS = {
  customerName: "Case Worker",
  agentName: "Case Worker",
  theme: "dark" as Theme,
  welcomeMessage:
    "Welcome. Ask a question about your document archive. Answers are generated only from the local corpus.",
  emptySources: "Ask a question to see sources.",
  readyStatus: "Ready.",
  healthLoading: "Loading database.",
  healthError: "Status could not be loaded.",
  startError: "Startup error"
} as const;

export const MAIN_APP_TEXT = {
  restoreSuccess: "Chat restored.",
  restoreError: "Chat could not be loaded.",
  newChatSuccess: "New conversation started.",
  newChatError: "New conversation could not be started.",
  sendError: "Fetch failed.",
  missingAnswer: "Could not generate an answer.",
  noReferencedSources: "Answer has no resolved citation tokens.",
  noNewSources: "Answer has no cited sources.",
  pipelineRootRequired: "Choose Pipeline Root Folder",
  pipelineWelcome: "Taxonomy Agent ready.",
  ontologyWelcome: "Ontology Agent ready.",
  thinking(agentName: string): string {
    return `${agentName} is thinking...`;
  },
  referencedSources(count: number): string {
    return `${count} sources referenced.`;
  }
} as const;

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function resolveLayoutMode(width: number, height: number): LayoutMode {
  if (width < 920 || height < 680) return "compact";
  if (width < 1440 || height < 820) return "laptop";
  return "wide";
}

export function resolveLayoutDensity(width: number, height: number): LayoutDensity {
  if (width < 1120 || height < 740) return "dense";
  if (width < 1480 || height < 860) return "compact";
  return "comfortable";
}

export function fitCustomerNameMinSize(density: LayoutDensity): number {
  if (density === "dense") return 12;
  if (density === "compact") return 13;
  return 14;
}

export function clampLayoutState(layout: LayoutState, shellWidth: number): LayoutState {
  const next = { ...layout };
  if (next.mode === "wide") {
    const usable = Math.max(
      LAYOUT_LIMITS.sidebar.min + LAYOUT_LIMITS.chat.min + LAYOUT_LIMITS.viewer.min,
      shellWidth - LAYOUT_LIMITS.resizer * 2
    );
    const sidebarMax = Math.min(
      LAYOUT_LIMITS.sidebar.max,
      usable - LAYOUT_LIMITS.chat.min - LAYOUT_LIMITS.viewer.min
    );
    next.sidebarWidth = clamp(next.sidebarWidth, LAYOUT_LIMITS.sidebar.min, Math.max(LAYOUT_LIMITS.sidebar.min, sidebarMax));
    const viewerMax = Math.min(
      LAYOUT_LIMITS.viewer.max,
      usable - LAYOUT_LIMITS.chat.min - next.sidebarWidth
    );
    next.viewerWidth = clamp(next.viewerWidth, LAYOUT_LIMITS.viewer.min, Math.max(LAYOUT_LIMITS.viewer.min, viewerMax));
    const remainingChat = usable - next.sidebarWidth - next.viewerWidth;
    if (remainingChat < LAYOUT_LIMITS.chat.min) {
      const deficit = LAYOUT_LIMITS.chat.min - remainingChat;
      const reducedViewer = Math.max(LAYOUT_LIMITS.viewer.min, next.viewerWidth - deficit);
      const remainingDeficit = deficit - (next.viewerWidth - reducedViewer);
      next.viewerWidth = reducedViewer;
      if (remainingDeficit > 0) next.sidebarWidth = Math.max(LAYOUT_LIMITS.sidebar.min, next.sidebarWidth - remainingDeficit);
    }
    next.secondaryWidth = clamp(next.secondaryWidth, LAYOUT_LIMITS.secondary.min, LAYOUT_LIMITS.secondary.max);
    return next;
  }

  const secondaryMax = Math.min(
    LAYOUT_LIMITS.secondary.max,
    Math.max(LAYOUT_LIMITS.secondary.min, shellWidth - LAYOUT_LIMITS.resizer - LAYOUT_LIMITS.chat.min)
  );
  next.secondaryWidth = clamp(next.secondaryWidth, LAYOUT_LIMITS.secondary.min, secondaryMax);
  return next;
}

export function createTurnCounterPresentation(turns: number, limit: number): TurnCounterPresentation {
  if (limit && turns >= limit) {
    return {
      text: `${turns}/${limit}`,
      title: "Chat length is starting to forget older context",
      state: "over"
    };
  }
  if (limit && turns >= Math.floor(limit * 0.75)) {
    return {
      text: `${turns}/${limit}`,
      title: `~${limit - turns} turns until context starts getting forgotten`,
      state: "warning"
    };
  }
  return {
    text: limit ? `${turns}/${limit}` : `${turns}`,
    title: "Question/answer turns in the current chat",
    state: null
  };
}

function formatTokenCount(value: number): string {
  const count = Math.max(0, Math.round(Number(value) || 0));
  if (count >= 1_000_000) {
    const millions = count / 1_000_000;
    return `${millions >= 10 ? Math.round(millions) : millions.toFixed(1)}M`;
  }
  if (count >= 1_000) {
    const thousands = count / 1_000;
    return `${thousands >= 10 ? Math.round(thousands) : thousands.toFixed(1)}k`;
  }
  return String(count);
}

export function createTokenCounterPresentation(inputTokens: number, outputTokens: number): TokenCounterPresentation {
  const input = Math.max(0, Math.round(Number(inputTokens) || 0));
  const output = Math.max(0, Math.round(Number(outputTokens) || 0));
  const total = input + output;
  return {
    text: `~In ${formatTokenCount(input)} | ~Out ${formatTokenCount(output)}`,
    title: `Estimated model tokens in this chat session. Input: ~${input.toLocaleString("en-US")} | Output: ~${output.toLocaleString("en-US")}.`,
    state: total >= 1_000_000 ? "over" : total >= 250_000 ? "warning" : null
  };
}
