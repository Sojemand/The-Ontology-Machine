import type { Source } from "../types/index.ts";
import type { UiMessage } from "./types.ts";
import { hasDirectMessageSources, isAssistantMessage, isValidSourceIndex } from "./validation.ts";

const CITATION_TOKEN_PATTERN = /\{\{\s*cite\s*:\s*doc\s*:\s*([^{}]+?)\s*\}\}/gi;

function mergeUniqueSources(...sourceGroups: Array<Source[] | undefined>): Source[] {
  const merged: Source[] = [];
  const seen = new Set<string>();

  sourceGroups.forEach((group) => {
    (Array.isArray(group) ? group : []).forEach((source) => {
      const id = String(source?.id || "").trim();
      const key = String(source?.source_key || id).trim();
      if (!id || !key || seen.has(key)) {
        return;
      }
      seen.add(key);
      merged.push(source);
    });
  });

  return merged;
}

export function parseCitationDocId(value: string): string {
  return String(value || "").trim();
}

export function findCitationSourceIndex(docId: string, sources: Source[]): number {
  const normalizedDocId = parseCitationDocId(docId);
  return sources.findIndex((source) => normalizedDocId && String(source?.id || "").trim() === normalizedDocId);
}

export function replaceCitationTokens(
  text: string,
  callback: (token: { raw: string; docId: string }) => string
): string {
  return String(text || "").replace(CITATION_TOKEN_PATTERN, (raw: string, docId: string) => {
    return callback({ raw, docId: parseCitationDocId(docId) });
  });
}

export function collectCitationDocIds(text: string): string[] {
  const ids: string[] = [];
  const seen = new Set<string>();
  replaceCitationTokens(text, ({ raw, docId }) => {
    if (docId && !seen.has(docId)) {
      seen.add(docId);
      ids.push(docId);
    }
    return raw;
  });
  return ids;
}

function collectReferencedSourceIndexes(
  text: string,
  sources: Source[] = []
): number[] {
  if (!text || !Array.isArray(sources) || !sources.length) {
    return [];
  }

  const referenced = new Set<number>();
  collectCitationDocIds(text).forEach((docId) => {
    const sourceIndex = findCitationSourceIndex(docId, sources);
    if (isValidSourceIndex(sourceIndex, sources)) referenced.add(sourceIndex);
  });

  return Array.from(referenced).sort((left, right) => left - right);
}

export function extractReferencedSources(
  text: string,
  sources: Source[] = []
): Source[] {
  return collectReferencedSourceIndexes(text, sources)
    .map((index) => sources[index])
    .filter(Boolean);
}

export function collectMessageSources(messages: UiMessage[]): Source[] {
  return mergeUniqueSources(...messages.map((message) => message.sources));
}

export function getMessageRenderSources(message: UiMessage | undefined, sourceCatalog: Source[] = []): Source[] {
  if (!isAssistantMessage(message)) {
    return [];
  }

  if (hasDirectMessageSources(message)) {
    return mergeUniqueSources(message.sources);
  }

  return [];
}

export function getMessageReferencedSources(message: UiMessage | undefined, sourceCatalog: Source[] = []): Source[] {
  if (!isAssistantMessage(message)) {
    return [];
  }

  const renderSources = getMessageRenderSources(message, sourceCatalog);
  return extractReferencedSources(message.content, renderSources);
}
