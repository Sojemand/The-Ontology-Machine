import type { ConfigResponse } from "../types/index.ts";
import type { ConfigAppState, Section, SectionState, SectionTokenField } from "./types.ts";

export interface ConfigWorkflowState {
  getState(): ConfigAppState;
  getCurrentConfig(): ConfigResponse | null;
  setCurrentConfig(config: ConfigResponse): void;
  getUnlocked(): boolean;
  setUnlocked(value: boolean): void;
  getConfigModelForSection(section: Section): string;
  getSectionModels(section: Section): string[];
  setSectionModels(section: Section, models: string[]): void;
  getLlmContextLimits(): Record<string, number | null>;
  setLlmContextLimits(limits: Record<string, number | null>): void;
  nextSectionToken(section: Section, key: SectionTokenField): number;
  isCurrentSectionToken(section: Section, key: SectionTokenField, token: number): boolean;
  nextSaveToken(): number;
  isCurrentSaveToken(token: number): boolean;
  nextUnlockToken(): number;
  isCurrentUnlockToken(token: number): boolean;
}

export function createConfigWorkflowState(): ConfigWorkflowState {
  const sectionState: Record<Section, SectionState> = {
    llm: { models: [], contextLimits: {}, refreshToken: 0, testToken: 0, deleteToken: 0 },
    embedding: { models: [], contextLimits: {}, refreshToken: 0, testToken: 0, deleteToken: 0 }
  };
  let currentConfig: ConfigResponse | null = null;
  let unlocked = false;
  let saveToken = 0;
  let unlockToken = 0;

  return {
    getState(): ConfigAppState {
      return {
        currentConfig,
        unlocked,
        llmModels: [...sectionState.llm.models],
        embeddingModels: [...sectionState.embedding.models],
        llmContextLimits: { ...sectionState.llm.contextLimits }
      };
    },
    getCurrentConfig() {
      return currentConfig;
    },
    setCurrentConfig(config) {
      currentConfig = config;
    },
    getUnlocked() {
      return unlocked;
    },
    setUnlocked(value) {
      unlocked = value;
    },
    getConfigModelForSection(section) {
      return section === "llm"
        ? currentConfig?.llm_model || "gpt-5.4"
        : currentConfig?.embedding_model || "text-embedding-3-small";
    },
    getSectionModels(section) {
      return [...sectionState[section].models];
    },
    setSectionModels(section, models) {
      sectionState[section].models = [...models];
    },
    getLlmContextLimits() {
      return { ...sectionState.llm.contextLimits };
    },
    setLlmContextLimits(limits) {
      sectionState.llm.contextLimits = { ...limits };
    },
    nextSectionToken(section, key) {
      const token = sectionState[section][key] + 1;
      sectionState[section][key] = token;
      return token;
    },
    isCurrentSectionToken(section, key, token) {
      return sectionState[section][key] === token;
    },
    nextSaveToken() {
      saveToken += 1;
      return saveToken;
    },
    isCurrentSaveToken(token) {
      return saveToken === token;
    },
    nextUnlockToken() {
      unlockToken += 1;
      return unlockToken;
    },
    isCurrentUnlockToken(token) {
      return unlockToken === token;
    }
  };
}
