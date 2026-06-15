export function validateRootDir(rootDir) {
  const normalizedRootDir = String(rootDir || "").trim();
  if (!normalizedRootDir) {
    throw new TypeError("rootDir ist erforderlich.");
  }
  return normalizedRootDir;
}

export function normalizeOwnerId(ownerId) {
  return String(ownerId || "").trim();
}

export function normalizeChatId(chatId) {
  return String(chatId || "").trim();
}

export function normalizeRecordArgs(input, legacyUserMsg, legacyAssistantAnswer) {
  if (input && typeof input === "object") {
    return {
      ownerId: normalizeOwnerId(input.ownerId),
      chatId: normalizeChatId(input.chatId),
      userMsg: input.userMsg,
      assistantAnswer: input.assistantAnswer
    };
  }

  const normalizedChatId = normalizeChatId(input);
  return {
    ownerId: normalizeOwnerId(input),
    chatId: normalizedChatId,
    userMsg: legacyUserMsg,
    assistantAnswer: legacyAssistantAnswer
  };
}

export function normalizeSearchArgs(input, legacyLimit) {
  const legacyMode = typeof input !== "object" || input == null;
  const normalizedInput = legacyMode ? { query: input, limit: legacyLimit } : input;
  return {
    legacyMode,
    ownerId: normalizeOwnerId(normalizedInput.ownerId),
    query: normalizedInput.query,
    limit: normalizedInput.limit
  };
}

export function normalizeRecentArgs(input) {
  const legacyMode = typeof input === "number";
  const normalizedInput = legacyMode ? { limit: input } : input || {};
  return {
    legacyMode,
    ownerId: normalizeOwnerId(normalizedInput.ownerId),
    limit: normalizedInput.limit
  };
}
