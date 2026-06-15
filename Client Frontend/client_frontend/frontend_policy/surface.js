import { cloneFrontendPolicy, DEFAULT_FRONTEND_POLICY } from "./defaults.js";
import { resolveFrontendPolicyPath, writeFrontendPolicyDocument } from "./repository.js";
import { loadFrontendPolicyWorkflow, prepareFrontendPolicyWorkflow } from "./workflow.js";
import { compileRegexDescriptors, normalizeFrontendPolicy } from "./validation.js";

function usePolicy(frontendPolicy) {
  return frontendPolicy ? normalizeFrontendPolicy(frontendPolicy) : cloneFrontendPolicy();
}

function dedupeStrings(values = []) {
  return Array.from(new Set((Array.isArray(values) ? values : []).map((value) => String(value || "").trim()).filter(Boolean)));
}

export { DEFAULT_FRONTEND_POLICY };

export function buildDefaultFrontendPolicy() {
  return cloneFrontendPolicy();
}

export async function loadFrontendPolicy(rootDir) {
  return await loadFrontendPolicyWorkflow(rootDir);
}

export async function saveFrontendPolicy(rootDir, frontendPolicy) {
  const normalized = prepareFrontendPolicyWorkflow(frontendPolicy);
  await writeFrontendPolicyDocument(rootDir, normalized);
  return normalized;
}

export function prepareFrontendPolicy(frontendPolicy) {
  return prepareFrontendPolicyWorkflow(frontendPolicy);
}

export function resolveFrontendPolicyPathForRoot(rootDir) {
  return resolveFrontendPolicyPath(rootDir);
}

export function resolveChatHistoryPolicy(frontendPolicy) {
  return usePolicy(frontendPolicy).chat_history;
}

export function resolveMemoryPolicy(frontendPolicy) {
  const policy = usePolicy(frontendPolicy).memory;
  return {
    ...policy,
    filler_patterns_compiled: compileRegexDescriptors(policy.filler_patterns),
    query_stop_words_set: new Set(policy.query_stop_words),
    topic_stop_words_set: new Set(policy.topic_stop_words),
    non_memory_answer_patterns_compiled: compileRegexDescriptors(policy.non_memory_answer_patterns)
  };
}

export function resolveModelCatalogPolicy(frontendPolicy) {
  const policy = usePolicy(frontendPolicy).model_catalog;
  return {
    ...policy,
    llm_seed_models: dedupeStrings(policy.llm_seed_models),
    embedding_seed_models: dedupeStrings(policy.embedding_seed_models)
  };
}

export function resolveMinAgentContextPolicy(frontendPolicy) {
  return usePolicy(frontendPolicy).min_agent.context;
}

export function resolveMinAgentRuntimePolicy(frontendPolicy) {
  return usePolicy(frontendPolicy).min_agent.runtime;
}

export function resolveMinAgentPromptPolicy(frontendPolicy) {
  return usePolicy(frontendPolicy).min_agent.prompt;
}

export function resolveOntologyAgentPromptPolicy(frontendPolicy) {
  return usePolicy(frontendPolicy).ontology_agent.prompt;
}
