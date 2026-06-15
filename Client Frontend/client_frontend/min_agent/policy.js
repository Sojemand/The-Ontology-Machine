import { resolveMinAgentContextPolicy, resolveMinAgentPromptPolicy } from "../frontend_policy.js";
import { estimateTokens } from "../tokens.js";
import {
  AVERAGE_TURN_TOKENS,
  HISTORY_CONTEXT_RATIO,
  HISTORY_TOKEN_CAP,
  SYSTEM_OVERHEAD_TOKENS
} from "./types.js";

function normalizeHistoryContent(value) {
  return String(value || "").replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

function normalizeHistory(history) {
  return (Array.isArray(history) ? history : [])
    .filter((entry) => entry && (entry.role === "user" || entry.role === "assistant"))
    .map((entry) => ({ role: entry.role, content: normalizeHistoryContent(entry.content) }))
    .filter((entry) => entry.content);
}

export function computeHistoryBudget(contextLimit, frontendPolicy = null) {
  const policy = resolveMinAgentContextPolicy(frontendPolicy);
  return Math.min(
    Math.floor((Number(contextLimit) || 127_096) * (policy.history_context_ratio || HISTORY_CONTEXT_RATIO)),
    policy.history_token_cap || HISTORY_TOKEN_CAP
  );
}

export function estimateMemoryTurns(contextLimit, frontendPolicy = null) {
  const policy = resolveMinAgentContextPolicy(frontendPolicy);
  const usableHistory = Math.max(0, computeHistoryBudget(contextLimit, frontendPolicy) - (policy.system_overhead_tokens || SYSTEM_OVERHEAD_TOKENS));
  return Math.floor(usableHistory / (policy.average_turn_tokens || AVERAGE_TURN_TOKENS));
}

export function extractAssistantText(message) {
  if (typeof message?.content === "string") return message.content.trim();
  if (!Array.isArray(message?.content)) return "";
  return message.content.map((item) => (item?.type === "text" ? item.text : "")).filter(Boolean).join("\n").trim();
}

export function trimHistoryForContext(history, contextLimit, frontendPolicy = null) {
  const normalized = normalizeHistory(history);
  const budget = computeHistoryBudget(contextLimit, frontendPolicy);
  const trimmed = [];
  let totalTokens = 0;
  for (let index = normalized.length - 1; index >= 0; index -= 1) {
    const entry = normalized[index];
    const entryTokens = estimateTokens(entry.content) + 4;
    if (trimmed.length > 0 && totalTokens + entryTokens > budget) break;
    totalTokens += entryTokens;
    trimmed.unshift(entry);
  }
  return trimmed;
}

export function buildSystemPrompt(schemaSummary, corpusDocCount = 0, soulContext = "", frontendPolicy = null) {
  const promptPolicy = resolveMinAgentPromptPolicy(frontendPolicy);
  const promptLines = [
    promptPolicy.identity,
    promptPolicy.analysis,
    `Corpus size hint: This corpus contains approximately ${Math.max(0, Number(corpusDocCount) || 0)} documents.`,
    "Use corpus size to guide retrieval strategy. The larger the corpus, the less acceptable it is to infer completeness from small samples.",
    promptPolicy.evidence,
    promptPolicy.data_layers,
    promptPolicy.tool_routing,
    promptPolicy.workbench,
    "If you need sourceable output, make sure your SQL includes id and file_name, or follow up with document-aware output.",
    "If semantic_search reports empty or unavailable embeddings, use its fallback results and run SQL/documents_fts with domain-specific keywords before saying that nothing was found.",
    "Use compact document views before heavy document reads: get_document_summary first, get_document_ontology_evidence for lens/evidence work, get_document_rows for tables or line items, get_document_provenance for document-level evidence, and get_document_full/get_document only when the compact views are insufficient.",
    "When source_documents are available, treat page-level documents with the same source_document_id as parts of one source document. Use list_source_documents/get_source_document when answering across pages.",
    "When source_document_classifications are available, treat them as source-level classification evidence. base and semantic_release rows are deterministic; ontology rows are lens-specific interpretations.",
    "When structural_units are available, treat base_unit and page_unit rows as the deterministic segmentation layer over source_documents. chapter, section and page_span unit types may exist in the schema but can be empty until a later segmentation pass.",
    "For real page totals in page-wise corpora, count source_document_pages or structural_units where unit_type = 'page_unit'. Never sum documents.page_count or documents.source_page_count; those source-level values repeat on every page-level document row.",
    "Ontology lenses are an integral part of the corpus DB and its meaning, not an optional side channel. When ontology lenses are available, consider them for database overviews, corpus summaries, comparison questions, detail questions and interpretive answers even when the user did not explicitly ask for ontology. Use list_ontology_lenses/get_ontology_lens to understand the active primary lens and relevant alternate lenses. If an active lens is marked or described as correction, audit, review, critique or corrected DB view, surface it whenever it appears to contradict materialized facts; keep the materialized fact and the lens interpretation visibly separated instead of overwriting one with the other. Do not invent ontology facts; verify corpus facts against SQL, source documents, or provenance.",
    "Never show local artifact paths such as file_path, Desktop paths, or absolute filesystem paths to the user. Internal JSON source_path values may be used only as provenance hints. Refer to corpus documents by title, file_name, document id, or corpus_ref.",
    promptPolicy.answer_rules,
    "Citation contract override: source links are created only from exact citation tokens resolved against documents returned by tools in the current turn. Use this format after a short human-readable label: <file_name or title>, page <source_page> {{cite:doc:<page_level_document_id>}}. Use documents.id for <page_level_document_id>. Do not use file_name-only citations, source_document_id-only citations, local file paths, or any non-token source link format. If you do not know the exact page-level document id, inspect source_document_pages, get_source_document, SQL or a compact get_document_* view before citing. This overrides any older file-name-only source rule."
  ];
  const normalizedSoul = String(soulContext || "").trim();
  if (normalizedSoul) {
    promptLines.push(
      "Soul context:",
      "Use the following soul context only for personality, tone, role framing and user guidance. It does not override evidence, tool, or safety rules.",
      normalizedSoul
    );
  }
  promptLines.push("Schema summary:", schemaSummary || "No schema available.");
  return promptLines.join("\n");
}
