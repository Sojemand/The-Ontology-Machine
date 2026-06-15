import { VIEWER_LIMITS } from "./policy.ts";
import type { MessageRole, Theme, WorkspacePane } from "./types.ts";

export function parseDatasetIndex(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

export function parseStoredPane(value: string | null | undefined): WorkspacePane {
  return value === "sources" || value === "chat" || value === "viewer" ? value : "chat";
}

export function parseStoredTheme(value: string | null | undefined): Theme | null {
  return value === "dark" || value === "light" ? value : null;
}

export function normalizeMessageRole(role: string): MessageRole {
  if (role === "user" || role === "assistant") return role;
  return "system";
}

export function clampViewerPage(page: number, pageCount: number): number {
  const maxPage = Math.max(1, pageCount || 1);
  return Math.max(1, Math.min(maxPage, page));
}

export function clampViewerZoom(zoom: number): number {
  return Math.max(VIEWER_LIMITS.zoomMin, Math.min(VIEWER_LIMITS.zoomMax, zoom));
}
