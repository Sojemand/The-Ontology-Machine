import type { ConfigResponse } from "../types/index.ts";
import type { ConfigDomAdapter, Section } from "./types.ts";
import type { ConfigWorkflowState } from "./workflow_state.ts";

interface DeleteApiKeyResponse {
  status: string;
  deleted: boolean;
  group: string;
  provider: string;
  base_url: string;
  message: string;
  config: ConfigResponse;
}

interface CredentialKeyWorkflowDeps {
  api: {
    deleteApiKey: (payload: Record<string, unknown>) => Promise<DeleteApiKeyResponse>;
  };
  adapter: ConfigDomAdapter;
  state: ConfigWorkflowState;
  applyConfig: (config: ConfigResponse) => void;
}

function groupForSection(section: Section): "llm_shared" | "embeddings" {
  return section === "embedding" ? "embeddings" : "llm_shared";
}

function configProvider(config: ConfigResponse, section: Section): string {
  return section === "embedding" ? config.embedding_provider : config.llm_provider;
}

function configBaseUrl(config: ConfigResponse, section: Section): string {
  return String(section === "embedding" ? config.embedding_base_url : config.llm_base_url).trim().replace(/\/+$/, "");
}

export function createCredentialKeyWorkflow({ api, adapter, state, applyConfig }: CredentialKeyWorkflowDeps) {
  return {
    async deleteApiKey(section: Section): Promise<void> {
      const token = state.nextSectionToken(section, "deleteToken");
      const provider = adapter.getProvider(section);
      const baseUrl = adapter.getSectionBaseUrl(section);
      adapter.setSectionStatus(section, `Deleting API key for ${provider}...`);
      try {
        const response = await api.deleteApiKey({
          group: groupForSection(section),
          provider,
          base_url: baseUrl
        });
        if (!state.isCurrentSectionToken(section, "deleteToken", token)) return;
        adapter.clearSectionApiKey(section);
        if (
          provider === configProvider(response.config, section)
          && baseUrl.replace(/\/+$/, "") === configBaseUrl(response.config, section)
        ) {
          applyConfig(response.config);
        } else {
          adapter.setSectionApiKeyCurrent(section, response.message);
        }
        adapter.setSectionStatus(section, response.message, response.deleted ? "ok" : "idle");
      } catch (error) {
        if (!state.isCurrentSectionToken(section, "deleteToken", token)) return;
        adapter.setSectionStatus(
          section,
          error instanceof Error ? error.message : "API key could not be deleted.",
          "error"
        );
      }
    }
  };
}
