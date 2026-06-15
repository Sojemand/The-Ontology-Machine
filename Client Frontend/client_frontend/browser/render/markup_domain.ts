import type { Source } from "../types/index.ts";
import { findCitationSourceIndex, replaceCitationTokens } from "./source_policy.ts";

export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderInlineSourceTag(label: string, messageIndex: number, sourceIndex: number): string {
  return `<button class="citation-button source-inline-tag" type="button" data-message-index="${messageIndex}" data-source-index="${sourceIndex}">${escapeHtml(label)}</button>`;
}

function renderUnresolvedSourceTag(label: string, title = "This citation token could not be resolved against the current source set."): string {
  return `<span class="source-unresolved-tag" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

function citationLabel(source: Source): string {
  const page = Number(source.source_page || source.page) || 0;
  return page > 0 ? `p.${page}` : "source";
}

function citationTitle(source: Source): string {
  const fileName = String(source.file_name || source.title || source.id || "source").trim();
  const page = Number(source.source_page || source.page) || 0;
  return page > 0 ? `${fileName}, page ${page}` : fileName;
}

function replaceCitationTokenMentions(text: string, sources: Source[], messageIndex: number): string {
  return replaceCitationTokens(text, ({ raw, docId }) => {
    const sourceIndex = findCitationSourceIndex(docId, sources);
    if (sourceIndex < 0) {
      return renderUnresolvedSourceTag("unresolved source", `Unresolved citation token: ${raw}`);
    }
    const source = sources[sourceIndex];
    return renderInlineSourceTag(citationLabel(source), messageIndex, sourceIndex).replace(
      "<button ",
      `<button title="${escapeHtml(citationTitle(source))}" `
    );
  });
}

function replaceInlineSourceBlocks(html: string, sources: Source[], messageIndex: number): string {
  return html
    .split(/(<[^>]+>)/g)
    .map((part) => (part.startsWith("<") ? part : replaceCitationTokenMentions(part, sources, messageIndex)))
    .join("");
}

export function formatInlineMarkup(
  text: string,
  sources: Source[],
  messageIndex: number,
  { preserveLineBreaks = true, allowBracketCitations = true }: { preserveLineBreaks?: boolean; allowBracketCitations?: boolean } = {}
): string {
  let html = escapeHtml(text);
  if (preserveLineBreaks) {
    html = html.replace(/\n/g, "<br>");
  }
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/`(.+?)`/g, "<code>$1</code>");
  html = replaceInlineSourceBlocks(html, sources, messageIndex);
  return html;
}
