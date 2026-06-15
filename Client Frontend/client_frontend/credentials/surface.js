import { createPendingLoginStore } from "./repository.js";
import {
  finishOAuthLogin,
  logoutFromOAuth,
  deleteRuntimeApiKey,
  resolveCredentialState,
  resolveLlmRuntime,
  resolveTargetApiKey,
  saveRuntimeApiKeys,
  startOAuthLogin
} from "./workflow.js";

export { createPendingLoginStore };

export async function getCredentialState(stateDir, runtimeConfig, modelCatalogState = null) {
  return await resolveCredentialState(stateDir, runtimeConfig, modelCatalogState);
}

export async function getLlmRuntime(stateDir, runtimeConfig) {
  return await resolveLlmRuntime(stateDir, runtimeConfig);
}

export async function getTargetApiKey(stateDir, target, runtimeConfig) {
  return await resolveTargetApiKey(stateDir, target, runtimeConfig);
}

export async function persistRuntimeApiKeys(stateDir, runtimeConfig) {
  return await saveRuntimeApiKeys(stateDir, runtimeConfig);
}

export async function deleteTargetApiKey(stateDir, target, runtimeConfig) {
  return await deleteRuntimeApiKey(stateDir, target, runtimeConfig);
}

export async function beginOAuthLogin(stateDir, callbackUrl, pendingLogins) {
  return await startOAuthLogin(stateDir, callbackUrl, pendingLogins);
}

export async function completeOAuthLogin(stateDir, callbackUrl, params, pendingLogins) {
  return await finishOAuthLogin(stateDir, callbackUrl, params, pendingLogins);
}

export async function clearOAuthSession(stateDir) {
  return await logoutFromOAuth(stateDir);
}
