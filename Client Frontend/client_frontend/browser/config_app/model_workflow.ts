import type { ConfigResponse, ModelsResponse } from "../types/index.ts";
import { buildContextHint, buildModelStatusText, resolveAutoFillBaseUrl, resolveSelectableModel } from "./policy.ts";
import type { ConfigDomAdapter, ProviderCatalogShape, Section } from "./types.ts";
import { assertSection } from "./validation.ts";
import type { ConfigWorkflowState } from "./workflow_state.ts";

interface ModelWorkflowDeps {
  api: {
    getModels: (params: Record<string, string>) => Promise<ModelsResponse>;
  };
  adapter: ConfigDomAdapter;
  catalog: ProviderCatalogShape;
  state: ConfigWorkflowState;
}

export function createModelWorkflow({ api, adapter, catalog, state }: ModelWorkflowDeps) {
  const renderSectionModels = (section: Section, preferredValue = "") => {
    const models = state.getSectionModels(section);
    const selected = resolveSelectableModel(models, [
      preferredValue,
      adapter.getSectionModel(section),
      state.getConfigModelForSection(section)
    ]);
    adapter.renderModelSelect(section, models, selected);
  };

  const updateContextHint = () =>
    adapter.setContextHint(
      buildContextHint(adapter.getContextLimitValue(), adapter.getSectionModel("llm"), state.getLlmContextLimits(), catalog)
    );

  const applyConfig = (config: ConfigResponse) => {
    state.setCurrentConfig(config);
    state.setSectionModels("llm", config.credential_state?.model_catalog?.llm_shared?.models || []);
    state.setSectionModels("embedding", config.credential_state?.model_catalog?.embeddings?.models || []);
    adapter.applyConfig(config);
    renderSectionModels("llm", config.llm_model || "gpt-5.4");
    renderSectionModels("embedding", config.embedding_model || "text-embedding-3-small");
    updateContextHint();
    adapter.applyLockState(Boolean(config.protected && !state.getUnlocked()));
  };

  const refreshModels = async (sectionName: Section): Promise<ModelsResponse | undefined> => {
    const section = assertSection(sectionName);
    const refreshToken = state.nextSectionToken(section, "refreshToken");
    const provider = adapter.getProvider(section);
    const baseUrl =
      adapter.getSectionBaseUrl(section) ||
      catalog.default_base_urls[provider as keyof typeof catalog.default_base_urls] ||
      "";
    const activeModel = adapter.getSectionModel(section) || state.getConfigModelForSection(section);

    try {
      const response = await api.getModels({
        group: section === "llm" ? "llm_shared" : "embeddings",
        provider,
        base_url: baseUrl,
        api_key: adapter.getSectionApiKey(section)
      });
      if (!state.isCurrentSectionToken(section, "refreshToken", refreshToken)) {
        return response;
      }
      const models = section === "llm" ? response.llm_models : response.embedding_models;
      state.setSectionModels(section, models);
      if (section === "llm" && response.context_limits) {
        state.setLlmContextLimits(response.context_limits);
      }
      renderSectionModels(section, activeModel);
      adapter.setSectionStatus(
        section,
        buildModelStatusText(response.source, models.length, response.error),
        response.source === "live" ? "ok" : response.error ? "error" : "idle"
      );
      updateContextHint();
      return response;
    } catch (error) {
      if (!state.isCurrentSectionToken(section, "refreshToken", refreshToken)) {
        return undefined;
      }
      adapter.setSectionStatus(
        section,
        error instanceof Error ? error.message : "Model list could not be loaded.",
        "error"
      );
      return undefined;
    }
  };

  const applyProviderAutoFill = (sectionName: Section, provider: string): void => {
    const section = assertSection(sectionName);
    const nextUrl = resolveAutoFillBaseUrl(provider, adapter.getSectionBaseUrl(section), catalog.default_base_urls);
    if (nextUrl) {
      adapter.setSectionBaseUrl(section, nextUrl);
    }
    adapter.syncProviderSensitiveStatus();
  };

  return { applyConfig, refreshModels, updateContextHint, applyProviderAutoFill };
}
