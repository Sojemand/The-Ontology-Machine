import { clampLimit, resolveMemoryRuntimePolicy, shouldStoreMemory } from "./policy.js";
import { buildRecordProjection, buildStoredProjection } from "./record_domain.js";
import { buildFtsQuery, buildPreparedQuery, buildSearchText, rankSearchRows } from "./search_domain.js";
import { serializeTopics, toPublicMemoryRow } from "./types.js";
import { normalizeRecentArgs, normalizeRecordArgs, normalizeSearchArgs } from "./validation.js";

function synchronizeStoredMemories(repository, frontendPolicy) {
  const hadSearchIndex = repository.hasSearchIndex?.() ?? false;
  let rowCount = 0;
  let changed = false;

  for (const row of repository.listMemoryRows()) {
    rowCount += 1;
    const projection = buildStoredProjection({
      ownerId: row.owner_id,
      chatId: row.chat_id,
      userMessage: row.user_message,
      assistantSummary: row.assistant_summary
    }, frontendPolicy);
    const topicsJson = serializeTopics(projection.topics);
    const searchText = buildSearchText(projection.userMessage, projection.assistantSummary, projection.topics, frontendPolicy);

    if (
      projection.ownerId !== row.owner_id ||
      projection.userMessage !== row.user_message ||
      projection.assistantSummary !== row.assistant_summary ||
      topicsJson !== row.topics ||
      searchText !== row.search_text
    ) {
      repository.updateMemoryProjection({
        id: row.id,
        ownerId: projection.ownerId,
        userMessage: projection.userMessage,
        assistantSummary: projection.assistantSummary,
        topicsJson,
        searchText
      });
      changed = true;
    }
  }

  if (changed || (rowCount > 0 && !hadSearchIndex)) {
    repository.rebuildSearchIndex();
  }
}

function recordMemory(repository, input, legacyUserMsg, legacyAssistantAnswer, frontendPolicy) {
  const projection = buildRecordProjection(normalizeRecordArgs(input, legacyUserMsg, legacyAssistantAnswer), frontendPolicy);
  if (!projection.ownerId || !projection.chatId) {
    return false;
  }
  if (!shouldStoreMemory(projection.userMessage, projection.assistantAnswer, projection.assistantSummary, frontendPolicy)) {
    return false;
  }

  repository.insertMemory({
    ownerId: projection.ownerId,
    chatId: projection.chatId,
    userMessage: projection.userMessage,
    assistantSummary: projection.assistantSummary,
    topicsJson: serializeTopics(projection.topics),
    searchText: buildSearchText(projection.userMessage, projection.assistantSummary, projection.topics, frontendPolicy),
    createdAt: Date.now()
  });
  return true;
}

function buildSearchResult(results, info, legacyMode) {
  if (legacyMode) {
    return results;
  }
  return info ? { results, info } : { results };
}

function searchMemories(repository, input, legacyLimit, frontendPolicy) {
  const searchInput = normalizeSearchArgs(input, legacyLimit);
  if (!searchInput.legacyMode && !searchInput.ownerId) {
    return { results: [], info: "No user context available for memory search." };
  }

  const preparedQuery = buildPreparedQuery(searchInput.query, frontendPolicy);
  if (!preparedQuery.keys.length) {
    return buildSearchResult([], "The search query is too broad for precise memory search.", searchInput.legacyMode);
  }

  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const limit = clampLimit(searchInput.limit, null, null, frontendPolicy);
  const rows = repository.searchRows({
    ownerId: searchInput.ownerId,
    ftsQuery: buildFtsQuery(preparedQuery.keys),
    limit: Math.max(limit * 8, policy.max_search_fetch),
    scoped: !searchInput.legacyMode
  });
  if (!rows.length) {
    return buildSearchResult([], "No matching memory found.", searchInput.legacyMode);
  }

  return buildSearchResult(
    rankSearchRows(rows, preparedQuery, limit, frontendPolicy).map(toPublicMemoryRow),
    "",
    searchInput.legacyMode
  );
}

function recentMemories(repository, input) {
  const recentInput = normalizeRecentArgs(input);
  const limit = clampLimit(recentInput.limit || 5, 5, 100);
  return repository.listRecent({ ownerId: recentInput.ownerId, limit }).map(toPublicMemoryRow);
}

export function createMemoryWorkflow({ repository, getFrontendPolicy = null }) {
  synchronizeStoredMemories(repository, getFrontendPolicy?.());
  return {
    record(input, legacyUserMsg, legacyAssistantAnswer) {
      return recordMemory(repository, input, legacyUserMsg, legacyAssistantAnswer, getFrontendPolicy?.());
    },
    search(input, legacyLimit) {
      return searchMemories(repository, input, legacyLimit ?? resolveMemoryRuntimePolicy(getFrontendPolicy?.()).max_search_results, getFrontendPolicy?.());
    },
    recent(input = {}) {
      return recentMemories(repository, input);
    },
    close() {
      repository.close();
    }
  };
}
