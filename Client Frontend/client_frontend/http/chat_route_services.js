import {
  getOntologySessionIdFromCookies,
  getPipelineSessionIdFromCookies,
  getSessionIdFromCookies,
  setOntologySessionCookie,
  setPipelineSessionCookie,
  setSessionCookie
} from "./adapter.js";

export const CHAT_HISTORY_PREFIX = "/api/chat/history/";
export const CHAT_RESTORE_PREFIX = "/api/chat/restore/";
export const ONTOLOGY_HISTORY_PREFIX = "/api/ontology-agent/history/";
export const ONTOLOGY_RESTORE_PREFIX = "/api/ontology-agent/restore/";
export const PIPELINE_HISTORY_PREFIX = "/api/pipeline-manager/history/";
export const PIPELINE_RESTORE_PREFIX = "/api/pipeline-manager/restore/";

export function queryServices(context) {
  return {
    agent: context.agent,
    sessionManager: context.sessionManager,
    chatStore: context.chatStore,
    getSessionIdFromCookies,
    setSessionCookie,
    historyPrefix: CHAT_HISTORY_PREFIX,
    restorePrefix: CHAT_RESTORE_PREFIX,
    memoryEnabled: true
  };
}

export function pipelineServices(context) {
  return {
    agent: context.pipelineAgent,
    sessionManager: context.pipelineSessionManager,
    chatStore: context.pipelineChatStore,
    getSessionIdFromCookies: getPipelineSessionIdFromCookies,
    setSessionCookie: setPipelineSessionCookie,
    historyPrefix: PIPELINE_HISTORY_PREFIX,
    restorePrefix: PIPELINE_RESTORE_PREFIX,
    memoryEnabled: false
  };
}

export function ontologyServices(context) {
  return {
    agent: context.ontologyAgent,
    sessionManager: context.ontologySessionManager,
    chatStore: context.ontologyChatStore,
    getSessionIdFromCookies: getOntologySessionIdFromCookies,
    setSessionCookie: setOntologySessionCookie,
    historyPrefix: ONTOLOGY_HISTORY_PREFIX,
    restorePrefix: ONTOLOGY_RESTORE_PREFIX,
    memoryEnabled: false
  };
}
