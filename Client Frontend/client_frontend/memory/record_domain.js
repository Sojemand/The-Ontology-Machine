import { resolveMemoryRuntimePolicy } from "./policy.js";

const ASCII_REPLACEMENTS = [
  [/\u00e4/g, "ae"], [/\u00f6/g, "oe"], [/\u00fc/g, "ue"], [/\u00df/g, "ss"],
  [/\u00c3\u00a4/g, "ae"], [/\u00c3\u00b6/g, "oe"], [/\u00c3\u00bc/g, "ue"], [/\u00c3\u009f/g, "ss"]
];
const PLAIN_ASCII_REPLACEMENTS = [
  [/\u00e4/g, "a"], [/\u00f6/g, "o"], [/\u00fc/g, "u"], [/\u00df/g, "ss"],
  [/\u00c3\u00a4/g, "a"], [/\u00c3\u00b6/g, "o"], [/\u00c3\u00bc/g, "u"], [/\u00c3\u009f/g, "ss"]
];

function replacePatterns(value, replacements) {
  let current = value;
  for (const [pattern, replacement] of replacements) current = current.replace(pattern, replacement);
  return current;
}

function collapseWhitespace(text) {
  return String(text || "").replace(/\r\n/g, "\n").replace(/\s+/g, " ").trim();
}

function stripCitations(text) {
  return String(text || "").replace(/\[\d+\]/g, " ");
}

function stripMarkdown(text) {
  return String(text || "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*_`>#]/g, " ")
    .replace(/^-+\s+/gm, " ");
}

function stripLegacyQuestionPrefix(text) {
  return String(text || "").replace(/^.{0,80}\s+(?:->|\u2192)\s+/u, "");
}

export function cleanStoredText(text) {
  return collapseWhitespace(stripMarkdown(stripCitations(text)));
}

function isFiller(sentence, frontendPolicy = null) {
  return resolveMemoryRuntimePolicy(frontendPolicy).filler_patterns_compiled.some((pattern) => pattern.test(cleanStoredText(sentence)));
}

function stripLeadingFiller(sentence, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  let current = cleanStoredText(sentence);
  let changed = true;
  while (changed && current) {
    changed = false;
    for (const pattern of policy.filler_patterns_compiled) {
      const next = current.replace(pattern, "").trim();
      if (next !== current) {
        current = next;
        changed = true;
      }
    }
  }
  return current;
}

function normalizeGermanAscii(text) {
  return replacePatterns(String(text || "").normalize("NFKC").toLowerCase(), ASCII_REPLACEMENTS)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function buildPlainAsciiVariant(text) {
  return replacePatterns(String(text || "").normalize("NFKC").toLowerCase(), PLAIN_ASCII_REPLACEMENTS)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function trimToken(rawToken) {
  return String(rawToken || "").replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
}

export function isLikelyIdentifier(rawToken) {
  return /[\d./-]/.test(rawToken);
}

export function buildLookupVariants(rawToken) {
  const token = trimToken(rawToken);
  if (!token) return [];

  const ascii = normalizeGermanAscii(token).replace(/[^a-z0-9./-]+/g, "");
  if (!ascii) return [];

  const variants = new Set([ascii]);
  const softened = buildPlainAsciiVariant(token).replace(/[^a-z0-9./-]+/g, "");
  if (softened && softened !== ascii) variants.add(softened);

  const compact = ascii.replace(/[^a-z0-9]/g, "");
  if (compact && compact !== ascii && compact.length >= 4) variants.add(compact);
  if (isLikelyIdentifier(token)) {
    for (const part of ascii.split(/[./-]+/)) if (part.length >= 3) variants.add(part);
  }
  return [...variants];
}

export function extractRawTokens(text) {
  return cleanStoredText(text).match(/[\p{L}\p{N}]+(?:[./-][\p{L}\p{N}]+)*/gu) || [];
}

export function extractSummary(answer, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const cleanedAnswer = cleanStoredText(stripLegacyQuestionPrefix(answer));
  if (!cleanedAnswer) return "";

  const segments = cleanedAnswer.split(/(?<=[.!?])\s+|\n+/u);
  const meaningful = segments
    .map((segment) => stripLeadingFiller(segment, frontendPolicy))
    .find((segment) => segment.length > 10 && !isFiller(segment, frontendPolicy));
  const fallback = segments.map((segment) => stripLeadingFiller(segment, frontendPolicy)).find((segment) => segment.length > 10);
  return cleanStoredText(meaningful || fallback || cleanedAnswer).slice(0, policy.max_summary_length);
}

function normalizeTopicCandidate(rawTopic) {
  return cleanStoredText(rawTopic).replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
}

function addTopic(topics, seen, value, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const cleaned = normalizeTopicCandidate(value);
  if (!cleaned) return;

  const lookupKey = buildLookupVariants(cleaned)[0] || normalizeGermanAscii(cleaned);
  if (!lookupKey || policy.topic_stop_words_set.has(lookupKey) || seen.has(lookupKey)) return;
  seen.add(lookupKey);
  topics.push(cleaned);
}

export function extractTopics(userMsg, answer, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const combined = `${cleanStoredText(userMsg)} ${cleanStoredText(answer).slice(0, 500)}`;
  const topics = [];
  const seen = new Set();
  const candidates = [
    ...(combined.match(/\b[\p{L}\p{N}]+(?:[./-][\p{L}\p{N}]+){1,}\b/gu) || []),
    ...(combined.match(/\b\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\b/g) || []),
    ...(combined.match(/\b\d[\d.,]*\s+\p{Lu}[\p{L}]{2,}\b/gu) || []),
    ...(combined.match(/\b[A-Z]{2,}(?:-[A-Z0-9]+)*\b/g) || []),
    ...extractRawTokens(combined).filter((token) => /^\p{Lu}/u.test(token) && token.length >= 3)
  ];

  for (const topic of candidates) {
    addTopic(topics, seen, topic, frontendPolicy);
    if (topics.length >= policy.max_topics) return topics;
  }
  return topics;
}

function buildBaseProjection(ownerId, chatId, userMessage) {
  const normalizedChatId = cleanStoredText(chatId);
  return {
    ownerId: cleanStoredText(ownerId) || normalizedChatId,
    chatId: normalizedChatId,
    userMessage: cleanStoredText(userMessage)
  };
}

export function buildStoredProjection({ ownerId, chatId, userMessage, assistantSummary }, frontendPolicy = null) {
  const base = buildBaseProjection(ownerId, chatId, userMessage);
  const cleanedSummary = extractSummary(assistantSummary, frontendPolicy);
  return { ...base, assistantSummary: cleanedSummary, topics: extractTopics(base.userMessage, cleanedSummary, frontendPolicy) };
}

export function buildRecordProjection({ ownerId, chatId, userMsg, assistantAnswer }, frontendPolicy = null) {
  const base = buildBaseProjection(ownerId, chatId, userMsg);
  const cleanedAssistantAnswer = cleanStoredText(assistantAnswer);
  const assistantSummary = extractSummary(cleanedAssistantAnswer, frontendPolicy);
  return {
    ...base,
    assistantAnswer: cleanedAssistantAnswer,
    assistantSummary,
    topics: extractTopics(base.userMessage, cleanedAssistantAnswer, frontendPolicy)
  };
}
