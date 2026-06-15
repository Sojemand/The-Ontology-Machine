import { resolveMemoryPolicy } from "../frontend_policy.js";

const SMALLTALK_PATTERNS = [
  /^(hallo|hi|hey|guten (tag|morgen|abend)|moin)[\s!.]*$/i,
  /^(danke|vielen dank|dankeschoen|merci)[\s!.]*$/i,
  /^(ja|nein|ok|okay|alles klar|verstanden|gut)[\s!.]*$/i,
  /^(tsch(?:uess|[u\u00fc]ss)|bye|bis (bald|dann|sp(?:aeter|\u00e4ter)))[\s!.]*$/i
];

export function resolveMemoryRuntimePolicy(frontendPolicy = null) {
  return resolveMemoryPolicy(frontendPolicy);
}

function isClarificationOnlyAnswer(cleanedAnswer) {
  if (!cleanedAnswer.toLowerCase().endsWith("?")) {
    return false;
  }
  return /(welches|welche|welcher|meinen sie|zu welchem|koennen sie|konnen sie|bitte)/i.test(cleanedAnswer);
}

export function shouldStoreMemory(cleanedUser, cleanedAnswer, assistantSummary, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  if (!cleanedUser || !cleanedAnswer || !assistantSummary) {
    return false;
  }
  if (SMALLTALK_PATTERNS.some((pattern) => pattern.test(cleanedUser))) {
    return false;
  }
  if (policy.non_memory_answer_patterns_compiled.some((pattern) => pattern.test(cleanedAnswer))) {
    return false;
  }
  return !isClarificationOnlyAnswer(cleanedAnswer);
}

export function clampLimit(limit, fallback = null, max = null, frontendPolicy = null) {
  const policy = resolveMemoryRuntimePolicy(frontendPolicy);
  const resolvedFallback = fallback ?? policy.max_search_results;
  const resolvedMax = max ?? policy.max_search_results;
  const numeric = Number(limit);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return resolvedFallback;
  }
  return Math.min(Math.floor(numeric), resolvedMax);
}
