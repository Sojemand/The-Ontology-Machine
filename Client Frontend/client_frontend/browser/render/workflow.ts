import type { Source } from "../types/index.ts";
import type { UiMessage } from "./types.ts";
import { formatInlineMarkup } from "./markup_domain.ts";
import { collectMessageSources, getMessageRenderSources } from "./source_policy.ts";
import { hasDirectMessageSources } from "./validation.ts";

function splitTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function isTableSeparatorLine(line: string): boolean {
  const cells = splitTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function isTableRowLine(line: string): boolean {
  return line.includes("|") && splitTableRow(line).length >= 2;
}

function normalizeCollapsedMarkdown(text: string): string {
  let output = String(text || "");
  output = output.replace(/([^\n])\s+(#{2,6}\s+)/g, "$1\n\n$2");
  if (!output.includes("|---")) {
    return output;
  }

  output = output.replace(/\|\s+\|(?=\s*:?-{3,}:?\|)/g, "|\n|");
  return output.replace(/\|\s+\|(?=\s*(?:`|\*\*|[A-Za-z0-9\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df(]))/g, "|\n|");
}

function splitLeadingTextFromTable(line: string): { text: string; tableLine: string } | null {
  const pipeIndex = line.indexOf("|");
  if (pipeIndex <= 0) {
    return null;
  }

  const text = line.slice(0, pipeIndex).trim();
  const tableLine = line.slice(pipeIndex).trim();
  return text && isTableRowLine(tableLine) ? { text, tableLine } : null;
}

function renderTableBlock(
  lines: string[],
  sources: Source[],
  messageIndex: number,
  allowBracketCitations: boolean
): string {
  const headerCells = splitTableRow(lines[0]);
  const bodyRows = lines
    .slice(2)
    .filter((line) => line.trim())
    .map((line) => splitTableRow(line));
  const columnCount = Math.max(headerCells.length, ...bodyRows.map((row) => row.length));
  const renderCell = (cell: string, tag: "th" | "td"): string => {
    const html = formatInlineMarkup(cell, sources, messageIndex, {
      preserveLineBreaks: false,
      allowBracketCitations
    });
    return `<${tag}>${html}</${tag}>`;
  };

  const headerHtml = `<thead><tr>${Array.from({ length: columnCount }, (_, index) => renderCell(headerCells[index] || "", "th")).join("")}</tr></thead>`;
  const bodyHtml = `<tbody>${bodyRows
    .map((row) => `<tr>${Array.from({ length: columnCount }, (_, index) => renderCell(row[index] || "", "td")).join("")}</tr>`)
    .join("")}</tbody>`;
  return `<div class="message-table-wrap"><table class="message-table">${headerHtml}${bodyHtml}</table></div>`;
}

function formatAnswer(text: string, sources: Source[], messageIndex: number, allowBracketCitations: boolean): string {
  const lines = normalizeCollapsedMarkdown(text).split(/\r?\n/);
  const blocks: string[] = [];

  for (let index = 0; index < lines.length; ) {
    const leadingTableText =
      index + 1 < lines.length && isTableSeparatorLine(lines[index + 1]) ? splitLeadingTextFromTable(lines[index]) : null;
    if (leadingTableText) {
      blocks.push(`<p>${formatInlineMarkup(leadingTableText.text, sources, messageIndex, { allowBracketCitations })}</p>`);
      lines[index] = leadingTableText.tableLine;
    }

    if (!lines[index].trim()) {
      index += 1;
      continue;
    }

    if (index + 1 < lines.length && isTableRowLine(lines[index]) && isTableSeparatorLine(lines[index + 1])) {
      const tableLines = [lines[index], lines[index + 1]];
      for (index += 2; index < lines.length && lines[index].trim() && isTableRowLine(lines[index]); index += 1) {
        tableLines.push(lines[index]);
      }
      blocks.push(renderTableBlock(tableLines, sources, messageIndex, allowBracketCitations));
      continue;
    }

    const paragraphLines: string[] = [];
    while (index < lines.length && lines[index].trim()) {
      if (index + 1 < lines.length && isTableRowLine(lines[index]) && isTableSeparatorLine(lines[index + 1])) {
        break;
      }
      paragraphLines.push(lines[index]);
      index += 1;
    }
    blocks.push(`<p>${formatInlineMarkup(paragraphLines.join("\n"), sources, messageIndex, { allowBracketCitations })}</p>`);
  }

  return blocks.join("");
}

export function renderMessagesHtml(messages: UiMessage[]): string {
  const sourceCatalog = collectMessageSources(messages);
  return messages
    .map((message, messageIndex) => {
      const className =
        message.role === "user"
          ? "message message-user"
          : message.role === "assistant"
            ? "message message-assistant"
            : "message message-system";
      const renderSources = getMessageRenderSources(message, sourceCatalog);
      const allowBracketCitations = hasDirectMessageSources(message);
      return `<article class="${className}">${formatAnswer(message.content, renderSources, messageIndex, allowBracketCitations)}</article>`;
    })
    .join("");
}
