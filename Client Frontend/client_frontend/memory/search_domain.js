import { resolveMemoryRuntimePolicy } from "./policy.js";
import { buildLookupVariants, cleanStoredText, extractRawTokens, isLikelyIdentifier } from "./record_domain.js";
import { parseTopics } from "./types.js";

function shouldKeepKey(key, policy, identifier = false) {
  if (!key) return false;
  if (identifier) {
    return key.replace(/[^a-z0-9]/g, "").length >= 3;
  }
  return key.length > 2 && !policy.query_stop_words_set.has(key);
}

function extractPrimaryKeys(text, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const keys = [];
  for (const rawToken of extractRawTokens(text)) {
    const primary = buildLookupVariants(rawToken)[0];
    if (shouldKeepKey(primary, policy, isLikelyIdentifier(rawToken))) {
      keys.push(primary);
    }
  }
  return keys;
}

export function extractLookupKeys(text, maxKeys = null, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const keys = [];
  const seen = new Set();
  const keyLimit = maxKeys ?? policy.max_query_keys;

  for (const rawToken of extractRawTokens(text)) {
    const identifier = isLikelyIdentifier(rawToken);
    for (const variant of buildLookupVariants(rawToken)) {
      if (!shouldKeepKey(variant, policy, identifier) || seen.has(variant)) {
        continue;
      }
      seen.add(variant);
      keys.push(variant);
      if (keys.length >= keyLimit) {
        return keys;
      }
    }
  }

  return keys;
}

export function buildSearchText(userMsg, assistantSummary, topics, frontendPolicy = null) {
  const combined = [userMsg, assistantSummary, ...topics].join(" ");
  return extractLookupKeys(combined, 128, frontendPolicy).join(" ");
}

export function buildPhraseKey(text, frontendPolicy = null) {
  return extractPrimaryKeys(text, frontendPolicy).slice(0, 10).join(" ");
}

function buildPhraseKeyWithResolvedPolicy(text, policy) {
  const keys = [];
  const seen = new Set();
  for (const rawToken of extractRawTokens(text)) {
    const primary = buildLookupVariants(rawToken)[0];
    if (shouldKeepKey(primary, policy, isLikelyIdentifier(rawToken)) && !seen.has(primary)) {
      seen.add(primary);
      keys.push(primary);
    }
  }
  return keys.slice(0, 10).join(" ");
}

export function buildPreparedQuery(query, frontendPolicy = null) {
  const cleanedQuery = cleanStoredText(query);
  return {
    cleanedQuery,
    keys: extractLookupKeys(cleanedQuery, null, frontendPolicy),
    phrase: buildPhraseKey(cleanedQuery, frontendPolicy),
    identifierKeys: extractRawTokens(cleanedQuery)
      .filter((token) => isLikelyIdentifier(token))
      .flatMap((token) => buildLookupVariants(token))
      .filter((key, index, values) => shouldKeepKey(key, resolveMemoryRuntimePolicy(frontendPolicy), true) && values.indexOf(key) === index)
  };
}

export function buildFtsQuery(keys) {
  return keys
    .map((key) => (/^[a-z]{4,}$/.test(key) ? `${key.replace(/"/g, "\"\"")}*` : `"${key.replace(/"/g, "\"\"")}"`))
    .join(" OR ");
}

function scoreCandidate(row, preparedQuery, policy, now = Date.now()) {
  const searchKeys = new Set(String(row.search_text || "").split(/\s+/).filter(Boolean));
  const primaryText = buildPhraseKeyWithResolvedPolicy(`${row.user_message} ${row.assistant_summary} ${parseTopics(row.topics).join(" ")}`, policy);
  const hitKeys = preparedQuery.keys.filter((key) => key && searchKeys.has(key));
  const ageMs = now - Number(row.created_at || 0);

  let recency = 0;
  if (ageMs <= policy.recent_days_high * 24 * 60 * 60 * 1000) {
    recency = 2;
  } else if (ageMs <= policy.recent_days_low * 24 * 60 * 60 * 1000) {
    recency = 1;
  }

  return {
    ...row,
    _match_keys: hitKeys,
    _score_exact_identifier: preparedQuery.identifierKeys.filter((key) => searchKeys.has(key)).length,
    _score_phrase: preparedQuery.phrase && primaryText.includes(preparedQuery.phrase) ? 1 : 0,
    _score_token_hits: hitKeys.length,
    _score_recency: recency,
    _score_fts: Number(row.text_rank) || 0
  };
}

function compareCandidates(left, right) {
  if (right._score_exact_identifier !== left._score_exact_identifier) {
    return right._score_exact_identifier - left._score_exact_identifier;
  }
  if (right._score_phrase !== left._score_phrase) {
    return right._score_phrase - left._score_phrase;
  }
  if (right._score_token_hits !== left._score_token_hits) {
    return right._score_token_hits - left._score_token_hits;
  }
  if (right._score_recency !== left._score_recency) {
    return right._score_recency - left._score_recency;
  }
  if (left._score_fts !== right._score_fts) {
    return left._score_fts - right._score_fts;
  }
  return Number(right.created_at || 0) - Number(left.created_at || 0);
}

function dedupeCandidates(candidates, limit) {
  const byChat = new Map();
  const selectedIds = new Set();
  const selected = [];

  for (const candidate of candidates) {
    if (byChat.has(candidate.chat_id)) {
      continue;
    }
    byChat.set(candidate.chat_id, { count: 1, matchedKeys: new Set(candidate._match_keys) });
    selectedIds.add(candidate.id);
    selected.push(candidate);
  }

  for (const candidate of candidates) {
    const state = byChat.get(candidate.chat_id);
    if (!state || state.count >= 2 || selectedIds.has(candidate.id)) {
      continue;
    }
    if (!candidate._match_keys.some((key) => !state.matchedKeys.has(key))) {
      continue;
    }
    state.count += 1;
    for (const key of candidate._match_keys) {
      state.matchedKeys.add(key);
    }
    selected.push(candidate);
  }

  return selected.slice(0, limit);
}

export function rankSearchRows(rows, preparedQuery, limit, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  return dedupeCandidates(rows.map((row) => scoreCandidate(row, preparedQuery, policy)).sort(compareCandidates), limit);
}
