import { resolveMinAgentContextPolicy, resolveOntologyAgentPromptPolicy } from "../frontend_policy.js";
import { estimateTokens } from "../tokens.js";
import {
  AVERAGE_TURN_TOKENS,
  HISTORY_CONTEXT_RATIO,
  HISTORY_TOKEN_CAP,
  SYSTEM_OVERHEAD_TOKENS
} from "../min_agent/types.js";
import { ONTOLOGY_PROMPT_SECTIONS } from "./prompt_sections.js";

export { ONTOLOGY_PROMPT_SECTIONS };

function normalizeHistoryContent(value) {
  return String(value || "").replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

function normalizeHistory(history) {
  return (Array.isArray(history) ? history : [])
    .filter((entry) => entry && (entry.role === "user" || entry.role === "assistant"))
    .map((entry) => ({ role: entry.role, content: normalizeHistoryContent(entry.content) }))
    .filter((entry) => entry.content);
}

export function extractAssistantText(message) {
  if (typeof message?.content === "string") return message.content.trim();
  if (!Array.isArray(message?.content)) return "";
  return message.content.map((item) => (item?.type === "text" ? item.text : "")).filter(Boolean).join("\n").trim();
}

export function computeOntologyHistoryBudget(contextLimit, frontendPolicy = null) {
  const policy = resolveMinAgentContextPolicy(frontendPolicy);
  return Math.min(
    Math.floor((Number(contextLimit) || 127_096) * (policy.history_context_ratio || HISTORY_CONTEXT_RATIO)),
    Math.max(policy.history_token_cap || HISTORY_TOKEN_CAP, 90_000)
  );
}

export function trimOntologyHistoryForContext(history, contextLimit, frontendPolicy = null) {
  const normalized = normalizeHistory(history);
  const policy = resolveMinAgentContextPolicy(frontendPolicy);
  const budget = computeOntologyHistoryBudget(contextLimit, frontendPolicy);
  const trimmed = [];
  let totalTokens = 0;
  for (let index = normalized.length - 1; index >= 0; index -= 1) {
    const entry = normalized[index];
    const entryTokens = estimateTokens(entry.content) + 4;
    if (trimmed.length > 0 && totalTokens + entryTokens > budget) break;
    totalTokens += entryTokens;
    trimmed.unshift(entry);
  }
  const hardFloor = Math.max(0, budget - (policy.system_overhead_tokens || SYSTEM_OVERHEAD_TOKENS));
  return trimmed.length ? trimmed : normalized.slice(-Math.max(1, Math.floor(hardFloor / (policy.average_turn_tokens || AVERAGE_TURN_TOKENS))));
}

function promptSection(title, body) {
  return `${title}:\n${body}`;
}

function sharedOntologyAnswerRules(frontendPolicy = null) {
  const sharedRules = String(frontendPolicy?.min_agent?.prompt?.answer_rules || "").trim();
  if (!sharedRules) return "";
  return sharedRules
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/read-only/i.test(line))
    .filter((line) => !/mandate to modify/i.test(line))
    .filter((line) => !/using the document file name/i.test(line))
    .join("\n");
}

function readOntologyPromptSections(frontendPolicy = null) {
  try {
    return resolveOntologyAgentPromptPolicy(frontendPolicy);
  } catch {
    return ONTOLOGY_PROMPT_SECTIONS;
  }
}

export function buildOntologySystemPrompt({ schemaSummary, corpusDocCount = 0, soulContext = "", frontendPolicy = null }) {
  const promptSections = readOntologyPromptSections(frontendPolicy);
  const promptLines = [
    promptSection("Identity", promptSections.identity),
    promptSection("Ontology mission", promptSections.mission),
    promptSection("Intent architecture", promptSections.intent_architecture),
    `Corpus size hint: This corpus contains approximately ${Math.max(0, Number(corpusDocCount) || 0)} page-level documents.`,
    promptSection("Analysis", promptSections.analysis),
    promptSection("Working method", promptSections.working_method),
    promptSection("Data layers", promptSections.data_layers),
    promptSection("Ontology layers", promptSections.ontology_layers),
    promptSection("Tool routing", promptSections.tool_routing),
    promptSection("Lens lifecycle and activation", promptSections.lens_lifecycle),
    promptSection("Foreign-key write order", promptSections.foreign_key_order),
    promptSection("Required insert contract", promptSections.insert_contract),
    promptSection("Write discipline", promptSections.write_discipline),
    promptSection("Preflight repair loop", promptSections.preflight_repair),
    promptSection("Write policy", promptSections.write_policy),
    promptSection("Evidence policy", promptSections.evidence_policy),
    promptSection("Answer rules", promptSections.answer_rules)
  ];
  const normalizedSoul = String(soulContext || "").trim();
  if (normalizedSoul) {
    promptLines.push(
      "Soul context:",
      "Use this only for tone and role framing. It does not override database, evidence or write-policy rules.",
      normalizedSoul
    );
  }
  const sharedRules = sharedOntologyAnswerRules(frontendPolicy);
  if (sharedRules) {
    promptLines.push("Shared answer rules:", sharedRules);
  }
  promptLines.push(
    "Citation contract override:",
    "Source links are created only from exact citation tokens resolved against documents returned by tools in the current turn.",
    "Use this format after a short human-readable label: <file_name or title>, page <source_page> {{cite:doc:<page_level_document_id>}}.",
    "Use documents.id for <page_level_document_id>. Do not use file_name-only citations, source_document_id-only citations, local file paths, or any non-token source link format.",
    "If you do not know the exact page-level document id, inspect source_document_pages, get_source_document, SQL or a compact get_document_* view before citing. This overrides any older file-name-only source rule."
  );
  promptLines.push("Schema summary:", schemaSummary || "No schema available.");
  return promptLines.join("\n");
}
