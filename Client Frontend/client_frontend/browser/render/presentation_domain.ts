import type { ChatHistoryEntry, Source } from "../types/index.ts";
import { escapeHtml } from "./markup_domain.ts";
import type { ViewerPresentation, ViewerRenderState } from "./types.ts";

export function renderSourcesHtml(sources: Source[], selectedSourceId: string | null): string {
  return sources
    .map((source, index) => {
      const active = selectedSourceId === source.id ? "active" : "";
      const refs = source.source_refs.length ? `<p class="source-refs muted">${escapeHtml(source.source_refs.join(", "))}</p>` : "";
      return `
        <button class="source-card ${active}" type="button" data-index="${index}">
          <div class="source-topline">
            <h3 class="source-title">${escapeHtml(source.title || source.id)}</h3>
            <span class="type-badge">${escapeHtml(source.type || "Document")}</span>
          </div>
          <div class="source-meta muted">
            <span>${escapeHtml(source.date || "no date")}</span>
            <span>${escapeHtml(source.actor || "no actor")}</span>
          </div>
          <p class="source-snippet">${escapeHtml(source.snippet || "No snippet available.")}</p>
          ${refs}
        </button>
      `;
    })
    .join("");
}

export function formatHistoryDate(epoch: number): string {
  const date = new Date(epoch);
  return `${date.toLocaleDateString("en-US")} ${date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
}

export function renderHistoryListHtml(chats: ChatHistoryEntry[]): string {
  if (!chats.length) {
    return '<p class="muted" style="padding: 16px;">No chats saved yet.</p>';
  }

  return chats
    .map((chat) => `
      <button class="history-entry" type="button" data-chat-id="${escapeHtml(chat.id)}">
        <div class="history-entry-title">${escapeHtml(chat.title || "Untitled Chat")}</div>
        <div class="history-entry-meta muted">${formatHistoryDate(chat.created_at)} \u00b7 ${chat.message_count} messages</div>
      </button>
    `)
    .join("");
}

export function buildViewerPresentation(viewer: ViewerRenderState): ViewerPresentation {
  const { selectedSource, page, imageFailed } = viewer;
  if (!selectedSource) {
    return {
      title: "No source selected",
      meta: "",
      pageLabel: "Page -/-",
      placeholderText: "Select a source to open the document view.",
      imageSrc: null,
      disablePrev: true,
      disableNext: true
    };
  }

  const title = selectedSource.title || selectedSource.id;
  const pageCount = selectedSource.page_count || 1;
  const viewerAvailable = selectedSource.viewer_available ?? false;
  const canAttemptImage = Boolean(selectedSource.image_url || selectedSource.id);
  const meta = `${selectedSource.type || "Document"} \u00b7 ${selectedSource.date || "no date"} \u00b7 ${selectedSource.actor || "no actor"}`;
  if (!viewerAvailable && !canAttemptImage) {
    return {
      title,
      meta,
      pageLabel: `Page ${page} / ${pageCount}`,
      placeholderText: "No page images are currently available for this document.",
      imageSrc: null,
      disablePrev: page <= 1,
      disableNext: page >= pageCount
    };
  }

  if (imageFailed) {
    return {
      title,
      meta,
      pageLabel: `Page ${page} / ${pageCount}`,
      placeholderText: "The requested page is currently unavailable.",
      imageSrc: null,
      disablePrev: page <= 1,
      disableNext: page >= pageCount
    };
  }

  return {
    title,
    meta,
    pageLabel: `Page ${page} / ${pageCount}`,
    placeholderText: null,
    imageSrc: `/api/image/${encodeURIComponent(selectedSource.id)}/${page}`,
    disablePrev: page <= 1,
    disableNext: page >= pageCount
  };
}
