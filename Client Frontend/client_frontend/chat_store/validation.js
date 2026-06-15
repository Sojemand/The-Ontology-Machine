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

export function hasScopedChatRequest(ownerId, chatId) {
  return Boolean(normalizeOwnerId(ownerId) && normalizeChatId(chatId));
}
