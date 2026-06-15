import type { ConnectionTestResponse } from "../types/index.ts";
import type { ConfigDomAdapter, ConfigFormPayload, Section } from "./types.ts";
import { assertSection } from "./validation.ts";
import type { ConfigWorkflowState } from "./workflow_state.ts";

interface ConnectionWorkflowDeps {
  api: {
    testEmbedding: (payload: Record<string, unknown>) => Promise<ConnectionTestResponse>;
    testLlm: (payload: Record<string, unknown>) => Promise<ConnectionTestResponse>;
  };
  adapter: ConfigDomAdapter;
  state: ConfigWorkflowState;
}

function buildTestPayload(section: Section, payload: ConfigFormPayload): Record<string, unknown> {
  return section === "llm"
    ? {
        provider: payload.llm_provider,
        base_url: payload.llm_base_url,
        api_key: payload.llm_api_key,
        model: payload.llm_model
      }
    : {
        provider: payload.embedding_provider,
        base_url: payload.embedding_base_url,
        api_key: payload.embedding_api_key,
        model: payload.embedding_model
      };
}

export function createConnectionWorkflow({ api, adapter, state }: ConnectionWorkflowDeps) {
  const runConnectionTest = async (sectionName: Section): Promise<ConnectionTestResponse | undefined> => {
    const section = assertSection(sectionName);
    const testToken = state.nextSectionToken(section, "testToken");
    adapter.setSectionStatus(section, "Testing connection...");

    try {
      const payload = adapter.collectPayload();
      const response =
        section === "llm"
          ? await api.testLlm(buildTestPayload(section, payload))
          : await api.testEmbedding(buildTestPayload(section, payload));
      if (!state.isCurrentSectionToken(section, "testToken", testToken)) {
        return response;
      }
      adapter.setSectionStatus(section, response.message, response.status);
      return response;
    } catch (error) {
      if (!state.isCurrentSectionToken(section, "testToken", testToken)) {
        return undefined;
      }
      adapter.setSectionStatus(
        section,
        error instanceof Error ? error.message : section === "llm" ? "LLM test failed." : "Embedding test failed.",
        "error"
      );
      return undefined;
    }
  };

  return { runConnectionTest };
}
