import type { Source } from "../types/index.ts";
import type { UiMessage } from "./types.ts";

export function isAssistantMessage(message: UiMessage | undefined): message is UiMessage & { role: "assistant" } {
  return Boolean(message?.role === "assistant");
}

export function hasDirectMessageSources(message: UiMessage | undefined): boolean {
  return isAssistantMessage(message) && Array.isArray(message.sources) && message.sources.length > 0;
}

export function isValidSourceIndex(sourceIndex: number, sources: Source[]): boolean {
  return Number.isInteger(sourceIndex) && sourceIndex >= 0 && sourceIndex < sources.length;
}
