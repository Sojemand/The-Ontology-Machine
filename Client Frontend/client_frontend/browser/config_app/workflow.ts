import type { ConfigResponse, ConnectionTestResponse, ModelsResponse } from "../types/index.ts";
import { createConnectionWorkflow } from "./connection_workflow.ts";
import { createCredentialKeyWorkflow } from "./credential_key_workflow.ts";
import { createModelWorkflow } from "./model_workflow.ts";
import { createOAuthWorkflow } from "./oauth_workflow.ts";
import { createSaveUnlockWorkflow } from "./save_unlock_workflow.ts";
import type {
  ConfigAppState,
  ConfigDomAdapter,
  ConfigFormPayload,
  ConfigWorkflow,
  ProviderCatalogShape,
  Section,
  StatusMode
} from "./types.ts";
import { createConfigWorkflowState } from "./workflow_state.ts";

interface WorkflowDeps {
  api: {
    getCurrentConfig: () => Promise<ConfigResponse>;
    getModels: (params: Record<string, string>) => Promise<ModelsResponse>;
    deleteApiKey: (payload: Record<string, unknown>) => Promise<{
      status: string;
      deleted: boolean;
      group: string;
      provider: string;
      base_url: string;
      message: string;
      config: ConfigResponse;
    }>;
    logoutOAuth: () => Promise<{ status: string; config: ConfigResponse }>;
    saveConfig: (payload: ConfigFormPayload) => Promise<{ status: string; config: ConfigResponse }>;
    testEmbedding: (payload: Record<string, unknown>) => Promise<ConnectionTestResponse>;
    testLlm: (payload: Record<string, unknown>) => Promise<ConnectionTestResponse>;
    unlockConfig: (secret: string) => Promise<{ status: string }>;
  };
  adapter: ConfigDomAdapter;
  catalog: ProviderCatalogShape;
}

export function createConfigWorkflow({ api, adapter, catalog }: WorkflowDeps): ConfigWorkflow {
  const state = createConfigWorkflowState();
  const modelWorkflow = createModelWorkflow({ api, adapter, catalog, state });
  const connectionWorkflow = createConnectionWorkflow({ api, adapter, state });
  const credentialKeyWorkflow = createCredentialKeyWorkflow({
    api,
    adapter,
    state,
    applyConfig: modelWorkflow.applyConfig
  });
  const saveUnlockWorkflow = createSaveUnlockWorkflow({
    api,
    adapter,
    state,
    applyConfig: modelWorkflow.applyConfig
  });
  const oauthWorkflow = createOAuthWorkflow({ api, adapter, state, applyConfig: modelWorkflow.applyConfig });

  return {
    async boot() {
      const config = await api.getCurrentConfig();
      state.setUnlocked(false);
      modelWorkflow.applyConfig(config);
      await modelWorkflow.refreshModels("llm");
      await modelWorkflow.refreshModels("embedding");
    },
    loginWithOAuth() {
      oauthWorkflow.loginWithOAuth();
    },
    logoutFromOAuth() {
      return oauthWorkflow.logoutFromOAuth();
    },
    refreshModels(section: Section): Promise<ModelsResponse | undefined> {
      return modelWorkflow.refreshModels(section);
    },
    deleteApiKey(section: Section): Promise<void> {
      return credentialKeyWorkflow.deleteApiKey(section);
    },
    runLlmTest() {
      return connectionWorkflow.runConnectionTest("llm");
    },
    runEmbeddingTest() {
      return connectionWorkflow.runConnectionTest("embedding");
    },
    submitSave: saveUnlockWorkflow.submitSave,
    submitUnlock: saveUnlockWorkflow.submitUnlock,
    setSaveStatus(text: string, mode: StatusMode = "idle") {
      saveUnlockWorkflow.setSaveStatus(text, mode);
    },
    updateContextHint() {
      modelWorkflow.updateContextHint();
    },
    applyProviderAutoFill(sectionName, provider) {
      modelWorkflow.applyProviderAutoFill(sectionName, provider);
    },
    getState(): ConfigAppState {
      return state.getState();
    }
  };
}
