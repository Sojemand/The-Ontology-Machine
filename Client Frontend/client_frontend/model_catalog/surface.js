import { loadModelCatalogState, refreshModelCatalog } from "./workflow.js";

export async function getModelCatalogState(stateDir, runtimeConfig, frontendPolicy = null) {
  return await loadModelCatalogState(stateDir, runtimeConfig, frontendPolicy);
}

export async function refreshModelCatalogGroup(stateDir, runtimeConfig, frontendPolicyOrRequest = null, requestOverride) {
  const request = requestOverride || frontendPolicyOrRequest;
  const frontendPolicy = requestOverride ? frontendPolicyOrRequest : null;
  return await refreshModelCatalog(stateDir, runtimeConfig, frontendPolicy, request);
}
