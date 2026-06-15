import { clampHistoryLimit, truncateTitle } from "./policy.js";
import { hasScopedChatRequest, normalizeChatId, normalizeOwnerId } from "./validation.js";
import { serializeMessages, toChatDetail, toChatListEntry } from "./types.js";

function saveChat(repository, ownerId, chatId, title, messages, frontendPolicy) {
  const normalizedOwnerId = normalizeOwnerId(ownerId);
  const normalizedChatId = normalizeChatId(chatId);
  if (!hasScopedChatRequest(normalizedOwnerId, normalizedChatId)) {
    return false;
  }

  const now = Date.now();
  const existing = repository.findChat(normalizedOwnerId, normalizedChatId);
  repository.saveChat({
    chatId: normalizedChatId,
    ownerId: normalizedOwnerId,
    title: truncateTitle(title, frontendPolicy),
    messages: serializeMessages(messages),
    createdAt: existing ? existing.created_at : now,
    updatedAt: now
  });
  return true;
}

function listChats(repository, ownerId, limit, frontendPolicy) {
  const normalizedOwnerId = normalizeOwnerId(ownerId);
  if (!normalizedOwnerId) {
    return [];
  }
  return repository.listChats(normalizedOwnerId, clampHistoryLimit(limit, frontendPolicy)).map(toChatListEntry);
}

function getChat(repository, ownerId, chatId) {
  const normalizedOwnerId = normalizeOwnerId(ownerId);
  const normalizedChatId = normalizeChatId(chatId);
  if (!hasScopedChatRequest(normalizedOwnerId, normalizedChatId)) {
    return null;
  }

  const row = repository.findChat(normalizedOwnerId, normalizedChatId);
  return row ? toChatDetail(row) : null;
}

function deleteChat(repository, ownerId, chatId) {
  const normalizedOwnerId = normalizeOwnerId(ownerId);
  const normalizedChatId = normalizeChatId(chatId);
  if (!hasScopedChatRequest(normalizedOwnerId, normalizedChatId)) {
    return false;
  }
  return repository.deleteChat(normalizedOwnerId, normalizedChatId);
}

export function createChatWorkflow({ repository, getFrontendPolicy = null }) {
  return {
    save(ownerId, chatId, title, messages) {
      return saveChat(repository, ownerId, chatId, title, messages, getFrontendPolicy?.());
    },
    list(ownerId, limit) {
      return listChats(repository, ownerId, limit, getFrontendPolicy?.());
    },
    get(ownerId, chatId) {
      return getChat(repository, ownerId, chatId);
    },
    delete(ownerId, chatId) {
      return deleteChat(repository, ownerId, chatId);
    },
    close() {
      repository.close();
    }
  };
}
