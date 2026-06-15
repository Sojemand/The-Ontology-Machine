import { mkdirSync } from "node:fs";
import path from "node:path";

import { ensureAppHomeLayout, migrateLegacyRootState } from "../app_paths.js";
import { createChatStore } from "../chat_store.js";
import { loadConfigState, resolveRuntimeConfig, saveConfigState } from "../config.js";
import { createPendingLoginStore, getCredentialState, persistRuntimeApiKeys } from "../credentials.js";
import { createMemoryStore } from "../memory.js";
import { getModelCatalogState } from "../model_catalog.js";
import { createMinimalAgent } from "../min_agent.js";
import { createOntologyAgent } from "../ontology_agent.js";
import { createPipelineManagerAgent } from "../pipeline_agent.js";
import { loadSoulProfile } from "./adapter.js";
import {
  createAgentFactory,
  createOntologyAgentFactory,
  createPipelineAgentFactory,
  ensureInstalledPipelineRootConfig
} from "./application_agents.js";
import { buildProtectedConfig } from "./policy.js";
import { createAdminSessionManager, createSessionManager } from "./repository.js";

export async function createApplicationContext({
  rootDir,
  appHome,
  configMode = false,
  createMinimalAgentFn = createMinimalAgent,
  createPipelineManagerAgentFn = createPipelineManagerAgent,
  createOntologyAgentFn = createOntologyAgent
}) {
  const appPaths = ensureAppHomeLayout({ moduleRoot: rootDir, appHome });
  migrateLegacyRootState({ moduleRoot: rootDir, appHome });
  const moduleRoot = appPaths.module_root;
  let { config, frontendPolicy, frontendPolicyDiagnostics } = await loadConfigState(appPaths.config_dir);
  const migratedSecrets = await persistRuntimeApiKeys(appPaths.state_dir, resolveRuntimeConfig(appPaths.config_dir, config));
  if (migratedSecrets.some((field) => field === "llm_api_key" || field === "embedding_api_key")) {
    const migratedState = await saveConfigState(
      appPaths.config_dir,
      { frontend_policy: frontendPolicy },
      { ...config, llm_api_key: "", embedding_api_key: "" }
    );
    config = migratedState.config;
    frontendPolicy = migratedState.frontendPolicy;
    frontendPolicyDiagnostics = migratedState.frontendPolicyDiagnostics;
  }
  config = await ensureInstalledPipelineRootConfig({ appPaths, moduleRoot, config });
  const getConfig = () => config;
  const getFrontendPolicy = () => frontendPolicy;
  const soulProfile = await loadSoulProfile(moduleRoot);
  const buildAgent = createAgentFactory({ moduleRoot, appPaths, getConfig, getFrontendPolicy, soulProfile, createMinimalAgentFn });
  const buildOntologyAgent = createOntologyAgentFactory({ moduleRoot, appPaths, getConfig, getFrontendPolicy, soulProfile, createOntologyAgentFn });
  const buildPipelineAgent = createPipelineAgentFactory({ moduleRoot, appPaths, getConfig, getFrontendPolicy, createPipelineManagerAgentFn });
  const pipelineStateDir = path.join(appPaths.state_dir, "pipeline_manager");
  const ontologyStateDir = path.join(appPaths.state_dir, "ontology_agent");
  mkdirSync(pipelineStateDir, { recursive: true });
  mkdirSync(ontologyStateDir, { recursive: true });
  let activeAgent = buildAgent(config);
  let activeOntologyAgent = buildOntologyAgent(config);
  let activePipelineAgent = buildPipelineAgent(config);
  void activePipelineAgent.initialize?.();

  const context = {
    rootDir: moduleRoot,
    appPaths,
    vaultDir: appPaths.config_dir,
    appDir: path.join(moduleRoot, "app"),
    serverStatePath: configMode ? appPaths.server_state_config_path : appPaths.server_state_chat_path,
    configMode,
    chatStore: createChatStore({ rootDir: appPaths.state_dir, getFrontendPolicy }),
    ontologyChatStore: createChatStore({ rootDir: ontologyStateDir, getFrontendPolicy }),
    pipelineChatStore: createChatStore({ rootDir: pipelineStateDir, getFrontendPolicy }),
    memoryStore: createMemoryStore({ rootDir: appPaths.state_dir, getFrontendPolicy }),
    sessionManager: createSessionManager(),
    ontologySessionManager: createSessionManager(),
    pipelineSessionManager: createSessionManager(),
    adminSessions: createAdminSessionManager(),
    oauthPendingLogins: createPendingLoginStore(),
    agentName: soulProfile.name,
    agent: activeAgent,
    ontologyAgent: activeOntologyAgent,
    pipelineAgent: activePipelineAgent,
    getConfig,
    getFrontendPolicy,
    getFrontendPolicyDiagnostics() {
      return frontendPolicyDiagnostics;
    },
    setConfig(nextConfig) {
      config = nextConfig;
    },
    setConfigState(nextState) {
      config = nextState.config;
      frontendPolicy = nextState.frontendPolicy;
      frontendPolicyDiagnostics = nextState.frontendPolicyDiagnostics || null;
    },
    reloadAgent(nextConfig = config) {
      const nextAgent = buildAgent(nextConfig);
      const nextOntologyAgent = buildOntologyAgent(nextConfig);
      const nextPipelineAgent = buildPipelineAgent(nextConfig);
      const previousAgent = activeAgent;
      const previousOntologyAgent = activeOntologyAgent;
      const previousPipelineAgent = activePipelineAgent;
      activeAgent = nextAgent;
      activeOntologyAgent = nextOntologyAgent;
      activePipelineAgent = nextPipelineAgent;
      context.agent = nextAgent;
      context.ontologyAgent = nextOntologyAgent;
      context.pipelineAgent = nextPipelineAgent;
      previousAgent.close();
      previousOntologyAgent.close();
      previousPipelineAgent.close();
      void nextPipelineAgent.initialize?.();
    },
    getRuntimeConfig() {
      return { ...resolveRuntimeConfig(appPaths.config_dir, config), state_dir: appPaths.state_dir };
    },
    async getCredentialState() {
      const runtimeConfig = context.getRuntimeConfig();
      return await getCredentialState(
        appPaths.state_dir,
        runtimeConfig,
        await getModelCatalogState(appPaths.state_dir, runtimeConfig, frontendPolicy)
      );
    },
    async getProtectedConfig() {
      return buildProtectedConfig(config, frontendPolicy, frontendPolicyDiagnostics, config.admin_secret, await context.getCredentialState());
    }
  };
  return context;
}
