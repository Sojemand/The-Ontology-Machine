import type { Section } from "./types.ts";

const SECTION_SET = new Set<Section>(["llm", "embedding"]);

export function assertSection(section: string): Section {
  if (SECTION_SET.has(section as Section)) {
    return section as Section;
  }
  throw new Error(`Unbekannte Config-Sektion: ${section}`);
}

export function hasUnlockSecret(secret: string): boolean {
  return String(secret || "").trim().length > 0;
}
