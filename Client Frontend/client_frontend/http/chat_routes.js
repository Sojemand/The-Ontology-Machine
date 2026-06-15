import { randomUUID } from "node:crypto";

import { SqlDatabasePathError } from "../config/database_path.js";
import { trimHistoryForContext } from "../min_agent.js";
import {
  getExistingUserId,
  json,
  parseCookies,
  readJsonBody,
  resolveUserId
} from "./adapter.js";
import {
  CHAT_HISTORY_PREFIX,
  CHAT_RESTORE_PREFIX,
  ONTOLOGY_HISTORY_PREFIX,
  ONTOLOGY_RESTORE_PREFIX,
  PIPELINE_HISTORY_PREFIX,
  PIPELINE_RESTORE_PREFIX,
  ontologyServices,
  pipelineServices,
  queryServices
} from "./chat_route_services.js";
import { buildChatPayload, buildDisplayMessages, getChatTitle, normalizeChatResult, toPublicChatMessage } from "./policy.js";
import { requireChatMessage, requireDecodedPathSuffix } from "./validation.js";

function appendDisplayMessages(context, sessionId, userMessage, result, services = queryServices(context)) {
  const nextMessages = [...services.sessionManager.getDisplayMessages(sessionId), ...buildDisplayMessages(userMessage, result)];
  services.sessionManager.setDisplayMessages(sessionId, nextMessages);
  return nextMessages;
}

function createSourceResolver(context, services = queryServices(context)) {
  return (sourceId) => services.agent?.resolveSource?.(sourceId) || null;
}

export function persistDisplayMessages(context, sessionId, services = queryServices(context)) {
  const ownerId = services.sessionManager.getOwnerId(sessionId);
  const displayMessages = services.sessionManager.getDisplayMessages(sessionId);
  if (!ownerId || !displayMessages.some((message) => message?.role === "user")) return;
  services.chatStore.save(ownerId, sessionId, getChatTitle(displayMessages), displayMessages);
}

export function persistPipelineDisplayMessages(context, sessionId) {
  persistDisplayMessages(context, sessionId, pipelineServices(context));
}

export function persistOntologyDisplayMessages(context, sessionId) {
  persistDisplayMessages(context, sessionId, ontologyServices(context));
}

async function handleAgentChatRoute({ request, response, context, services }) {
  const message = requireChatMessage(await readJsonBody(request));
  const cookies = parseCookies(request.headers.cookie);
  const sessionIdFromCookie = services.getSessionIdFromCookies(context.vaultDir, cookies);
  const sessionId = sessionIdFromCookie || randomUUID();
  await services.sessionManager.runSerialized(sessionId, async () => {
    if (!sessionIdFromCookie) services.setSessionCookie(context.vaultDir, response, sessionId, request);
    const ownerId = resolveUserId(context.vaultDir, response, cookies, sessionId, request);
    services.sessionManager.setOwnerId(sessionId, ownerId);
    services.sessionManager.touch(sessionId);
    const history = services.sessionManager.getHistory(sessionId);
    let result;
    try {
      result = normalizeChatResult(await services.agent.chat({ message, history, ownerId }), history, message);
    } catch (error) {
      if (error instanceof SqlDatabasePathError) {
        json(response, 409, { error: error.message, field: error.field });
        return;
      }
      throw error;
    }
    services.sessionManager.setHistory(sessionId, result.history);
    services.sessionManager.touch(sessionId);
    const displayMessages = appendDisplayMessages(context, sessionId, message, result, services);
    services.chatStore.save(ownerId, sessionId, getChatTitle(displayMessages), displayMessages);
    if (services.memoryEnabled) context.memoryStore.record({ ownerId, chatId: sessionId, userMsg: message, assistantAnswer: result.answer });
    json(response, 200, buildChatPayload(result));
  });
}

async function handleChatRouteV2({ request, response, context }) {
  await handleAgentChatRoute({ request, response, context, services: queryServices(context) });
}

async function handlePipelineChatRoute({ request, response, context }) {
  try {
    await handleAgentChatRoute({ request, response, context, services: pipelineServices(context) });
  } catch (error) {
    if (error?.code === "pipeline_manager_unavailable") {
      json(response, 409, { error: error.message, field: "pipeline_root" });
      return;
    }
    throw error;
  }
}

async function handleOntologyChatRoute({ request, response, context }) {
  await handleAgentChatRoute({ request, response, context, services: ontologyServices(context) });
}

async function handleChatHistoryListRoute({ request, response, context, services = queryServices(context) }) {
  json(response, 200, { chats: services.chatStore.list(getExistingUserId(context.vaultDir, parseCookies(request.headers.cookie))) });
}

async function handleNewChatRoute({ request, response, context, services = queryServices(context) }) {
  const cookies = parseCookies(request.headers.cookie);
  const oldSessionId = services.getSessionIdFromCookies(context.vaultDir, cookies);
  const newSessionId = randomUUID();
  await services.sessionManager.runSerialized(oldSessionId || newSessionId, async () => {
    const ownerId = resolveUserId(context.vaultDir, response, cookies, oldSessionId || newSessionId, request);
    if (oldSessionId) {
      persistDisplayMessages(context, oldSessionId, services);
      services.sessionManager.deleteSession(oldSessionId);
    }
    services.sessionManager.setOwnerId(newSessionId, ownerId);
      services.setSessionCookie(context.vaultDir, response, newSessionId, request);
    json(response, 200, { status: "ok" });
  });
}

async function handleChatHistoryGetRoute({ request, response, url, context, services = queryServices(context) }) {
  const chat = services.chatStore.get(
    getExistingUserId(context.vaultDir, parseCookies(request.headers.cookie)),
    requireDecodedPathSuffix(url.pathname, services.historyPrefix, "Chat-ID")
  );
  if (!chat) {
    json(response, 404, { error: "Chat not found." });
    return;
  }
  json(response, 200, { ...chat, messages: chat.messages.map((message) => toPublicChatMessage(message, createSourceResolver(context, services))) });
}

async function handleChatHistoryDeleteRoute({ request, response, url, context, services = queryServices(context) }) {
  const deleted = services.chatStore.delete(
    getExistingUserId(context.vaultDir, parseCookies(request.headers.cookie)),
    requireDecodedPathSuffix(url.pathname, services.historyPrefix, "Chat-ID")
  );
  json(response, deleted ? 200 : 404, deleted ? { status: "ok" } : { error: "Chat not found." });
}

async function handleChatRestoreRoute({ request, response, url, context, services = queryServices(context) }) {
  const cookies = parseCookies(request.headers.cookie);
  const ownerId = getExistingUserId(context.vaultDir, cookies);
  const chat = services.chatStore.get(ownerId, requireDecodedPathSuffix(url.pathname, services.restorePrefix, "Chat-ID"));
  if (!chat) {
    json(response, 404, { error: "Chat not found." });
    return;
  }
  const sessionIdFromCookie = services.getSessionIdFromCookies(context.vaultDir, cookies);
  const sessionId = sessionIdFromCookie || randomUUID();
  await services.sessionManager.runSerialized(sessionId, async () => {
    if (!sessionIdFromCookie) services.setSessionCookie(context.vaultDir, response, sessionId, request);
    services.sessionManager.setOwnerId(sessionId, resolveUserId(context.vaultDir, response, cookies, sessionId, request));
    const publicMessages = chat.messages.map((message) => toPublicChatMessage(message, createSourceResolver(context, services)));
    const agentHistory = chat.messages
      .filter((message) => message.role === "user" || message.role === "assistant")
      .map((message) => ({ role: message.role, content: message.content }));
    services.sessionManager.setHistory(sessionId, trimHistoryForContext(agentHistory, context.getRuntimeConfig().context_limit, context.getFrontendPolicy()));
    services.sessionManager.setDisplayMessages(sessionId, publicMessages);
    services.sessionManager.touch(sessionId);
    json(response, 200, { messages: publicMessages, title: chat.title });
  });
}

export function createChatRoutes({ exact, prefix }) {
  return [
    exact("v2-chat", "workflow", "POST", "/api/v2/chat", handleChatRouteV2),
    exact("pipeline-chat", "workflow", "POST", "/api/v2/pipeline-manager/chat", handlePipelineChatRoute),
    exact("ontology-chat", "workflow", "POST", "/api/v2/ontology-agent/chat", handleOntologyChatRoute),
    exact("chat-history-list", "workflow", "GET", "/api/chat/history", handleChatHistoryListRoute),
    exact("chat-new", "workflow", "POST", "/api/chat/new", handleNewChatRoute),
    prefix("chat-history-detail", "workflow", "GET", CHAT_HISTORY_PREFIX, handleChatHistoryGetRoute),
    prefix("chat-history-delete", "workflow", "DELETE", CHAT_HISTORY_PREFIX, handleChatHistoryDeleteRoute),
    prefix("chat-restore", "workflow", "POST", CHAT_RESTORE_PREFIX, handleChatRestoreRoute),
    exact("pipeline-history-list", "workflow", "GET", "/api/pipeline-manager/history", (args) => handleChatHistoryListRoute({ ...args, services: pipelineServices(args.context) })),
    exact("pipeline-new", "workflow", "POST", "/api/pipeline-manager/new", (args) => handleNewChatRoute({ ...args, services: pipelineServices(args.context) })),
    prefix("pipeline-history-detail", "workflow", "GET", PIPELINE_HISTORY_PREFIX, (args) => handleChatHistoryGetRoute({ ...args, services: pipelineServices(args.context) })),
    prefix("pipeline-history-delete", "workflow", "DELETE", PIPELINE_HISTORY_PREFIX, (args) => handleChatHistoryDeleteRoute({ ...args, services: pipelineServices(args.context) })),
    prefix("pipeline-restore", "workflow", "POST", PIPELINE_RESTORE_PREFIX, (args) => handleChatRestoreRoute({ ...args, services: pipelineServices(args.context) })),
    exact("ontology-history-list", "workflow", "GET", "/api/ontology-agent/history", (args) => handleChatHistoryListRoute({ ...args, services: ontologyServices(args.context) })),
    exact("ontology-new", "workflow", "POST", "/api/ontology-agent/new", (args) => handleNewChatRoute({ ...args, services: ontologyServices(args.context) })),
    prefix("ontology-history-detail", "workflow", "GET", ONTOLOGY_HISTORY_PREFIX, (args) => handleChatHistoryGetRoute({ ...args, services: ontologyServices(args.context) })),
    prefix("ontology-history-delete", "workflow", "DELETE", ONTOLOGY_HISTORY_PREFIX, (args) => handleChatHistoryDeleteRoute({ ...args, services: ontologyServices(args.context) })),
    prefix("ontology-restore", "workflow", "POST", ONTOLOGY_RESTORE_PREFIX, (args) => handleChatRestoreRoute({ ...args, services: ontologyServices(args.context) }))
  ];
}
