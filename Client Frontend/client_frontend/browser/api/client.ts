export { routeForAgent } from "./agent_routes.ts";
export type { ChatAgentType } from "./agent_routes.ts";
export { createApiClient } from "./factory.ts";
export type { ApiClient } from "./factory.ts";
export { ApiError, extractErrorMessage, requestWithFetch } from "./transport.ts";

import { createApiClient } from "./factory.ts";

const defaultClient = createApiClient();

export const getHealth = defaultClient.getHealth;
export const sendChat = defaultClient.sendChat;
export const getCurrentConfig = defaultClient.getCurrentConfig;
export const getModels = defaultClient.getModels;
export const deleteApiKey = defaultClient.deleteApiKey;
export const testLlm = defaultClient.testLlm;
export const testEmbedding = defaultClient.testEmbedding;
export const unlockConfig = defaultClient.unlockConfig;
export const logoutOAuth = defaultClient.logoutOAuth;
export const saveConfig = defaultClient.saveConfig;
export const getChatHistory = defaultClient.getChatHistory;
export const newChat = defaultClient.newChat;
export const restoreChat = defaultClient.restoreChat;
export const cancelPipelineRun = defaultClient.cancelPipelineRun;
export const resetKernelRuntimeState = defaultClient.resetKernelRuntimeState;
export const getPipelineKernelEvents = defaultClient.getPipelineKernelEvents;
export const submitKernelInteractionResponse = defaultClient.submitKernelInteractionResponse;
export const cancelKernelInteraction = defaultClient.cancelKernelInteraction;
