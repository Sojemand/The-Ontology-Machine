import { cloneFrontendPolicy } from "./defaults.js";
import { readFrontendPolicyDocument, writeFrontendPolicyDocument } from "./repository.js";
import { FrontendPolicyValidationError, normalizeFrontendPolicy } from "./validation.js";

const LEGACY_DEFAULT_LLM_SEED_MODEL_SETS = [
  [
    "gpt-5.5-pro",
    "gpt-5.5",
    "gpt-5.4-pro",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.2-pro",
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5-pro",
    "gpt-5",
    "gpt-5-chat-latest",
    "gpt-5-mini",
    "gpt-5-nano"
  ],
  [
    "gpt-5.4-pro",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1"
  ],
  [
    "gpt-4.1",
    "gpt-5.4-pro",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano"
  ],
  [
    "gpt-4.1",
    "gpt-5.4-pro",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o-mini"
  ]
];
const LEGACY_FILE_NAME_ONLY_SOURCE_RULE = "Always name the source where you found the information using the document file name. Do not use any other source format.";
const LEGACY_BRACKET_SOURCE_RULE = "Do not use bracket citations like [1] or [10] for sources; they are not machine-readable source references.";
const TOKEN_ONLY_SOURCE_RULE = "Use citation tokens as the only machine-readable source link format.";

function buildDiagnostics(status, message, rawText, policyPath = null) {
  return { status, message, raw_text: rawText, ...(policyPath ? { policy_path: policyPath } : {}) };
}

export async function loadFrontendPolicyWorkflow(rootDir) {
  const defaults = cloneFrontendPolicy();
  const document = await readFrontendPolicyDocument(rootDir);
  if (document.status === "missing") {
    await writeFrontendPolicyDocument(rootDir, defaults);
    return { frontendPolicy: defaults, frontendPolicyDiagnostics: null };
  }
  if (document.status === "invalid_json") {
    return {
      frontendPolicy: defaults,
      frontendPolicyDiagnostics: buildDiagnostics(
        "invalid_json",
        `frontend_policy.json is not valid JSON: ${document.reason || "Unknown error."}`,
        document.raw
      )
    };
  }
  try {
    const normalized = migrateFrontendPolicyDefaults(normalizeFrontendPolicy(document.parsed), defaults);
    if (normalized.migrated) {
      await writeFrontendPolicyDocument(rootDir, normalized.frontendPolicy);
    }
    return {
      frontendPolicy: normalized.frontendPolicy,
      frontendPolicyDiagnostics: null
    };
  } catch (error) {
    if (!(error instanceof FrontendPolicyValidationError)) {
      throw error;
    }
    return {
      frontendPolicy: defaults,
      frontendPolicyDiagnostics: buildDiagnostics(error.status, error.message, document.raw, error.policy_path)
    };
  }
}

export function prepareFrontendPolicyWorkflow(payload) {
  return normalizeFrontendPolicy(payload);
}

export function migrateFrontendPolicyDefaults(frontendPolicy, defaults = cloneFrontendPolicy()) {
  const normalized = normalizeFrontendPolicy(frontendPolicy);
  const next = clonePolicy(normalized);
  let migrated = false;
  if (isLegacyDefaultSeedList(next.model_catalog.llm_seed_models)) {
    next.model_catalog.llm_seed_models = [...defaults.model_catalog.llm_seed_models];
    migrated = true;
  }
  if (isLegacyDefaultEmbeddingSeedList(next.model_catalog.embedding_seed_models)) {
    next.model_catalog.embedding_seed_models = [...defaults.model_catalog.embedding_seed_models];
    migrated = true;
  }
  if (String(next.min_agent?.prompt?.answer_rules || "").includes(LEGACY_FILE_NAME_ONLY_SOURCE_RULE)) {
    next.min_agent.prompt.answer_rules = String(next.min_agent.prompt.answer_rules).replace(
      LEGACY_FILE_NAME_ONLY_SOURCE_RULE,
      defaults.min_agent.prompt.answer_rules
        .split("\n")
        .filter((line) => /citation token|page-level|machine-readable source link|actually returned by tools/i.test(line))
        .join("\n")
    );
    migrated = true;
  }
  if (replaceLegacyBracketSourceRule(next.min_agent?.prompt)) migrated = true;
  if (replaceLegacyBracketSourceRule(next.ontology_agent?.prompt)) migrated = true;
  return { frontendPolicy: next, migrated };
}

function replaceLegacyBracketSourceRule(prompt) {
  if (!prompt || typeof prompt.answer_rules !== "string" || !prompt.answer_rules.includes(LEGACY_BRACKET_SOURCE_RULE)) {
    return false;
  }
  prompt.answer_rules = prompt.answer_rules.replace(LEGACY_BRACKET_SOURCE_RULE, TOKEN_ONLY_SOURCE_RULE);
  return true;
}

function clonePolicy(policy) {
  return JSON.parse(JSON.stringify(policy));
}

function normalizeList(values) {
  return (Array.isArray(values) ? values : []).map((value) => String(value || "").trim()).filter(Boolean);
}

function sameList(left, right) {
  const leftValues = normalizeList(left);
  const rightValues = normalizeList(right);
  return leftValues.length === rightValues.length && leftValues.every((value, index) => value === rightValues[index]);
}

function isLegacyDefaultSeedList(values) {
  return LEGACY_DEFAULT_LLM_SEED_MODEL_SETS.some((legacy) => sameList(values, legacy));
}

function isLegacyDefaultEmbeddingSeedList(values) {
  return sameList(values, ["text-embedding-3-small"]);
}
