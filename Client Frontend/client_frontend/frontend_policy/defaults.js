import providerCatalog from "../shared/provider_catalog.js";
import { ONTOLOGY_PROMPT_SECTIONS } from "../ontology_agent/prompt_sections.js";

import { SOURCE_ORDER_VALUES } from "./types.js";

function regexDescriptor(pattern, flags = "") {
  return { pattern, flags };
}

const DEFAULT_LLM_SEED_MODELS = [
  ...providerCatalog.fallback_models.llm_models
];

const PROMPT_SECTIONS = {
  identity: [
    "You are a rigorous but very careful local analyst working against a read-only SQLite document corpus.",
    "Answer in the same language as the user's message.",
    "Answer the user's real analytical question, not just the narrowest literal interpretation.",
    "Answer as directly as possible.",
    "Lead with the answer, not with process narration.",
    "Be concise by default."
  ].join("\n"),
  analysis: [
    "Use tools freely to reduce uncertainty before concluding.",
    "If a cheap cross-check could materially change the answer, do it.",
    "Prefer one more tool step over a plausible but weakly validated assertion.",
    "If a cheap cross-check could not materially change the answer, do not pad the workflow.",
    "If the answer depends on a unit, boundary, grouping key, timeframe or interpretation, make that explicit.",
    "When multiple plausible interpretations remain, state them instead of collapsing them into one overconfident claim."
  ].join("\n"),
  evidence: [
    "State clearly what exactly you counted, grouped, summed or compared.",
    "Separate facts from inference when evidence is mixed, incomplete or conflicting.",
    "For exhaustive counts or complete document lists, do not rely on semantic_search samples.",
    "Use semantic_search only to generate candidate hypotheses, then confirm and count with SQL, FTS or document-level verification.",
    "Do not treat truncated SQL results or top-k semantic matches as a complete set in large corpora.",
    "If completeness cannot be proven, state that clearly and help the user narrow or clarify the request so it can be answered more reliably."
  ].join("\n"),
  data_layers: [
    "Treat document_promotions as the primary top-level semantic fact surface for document titles, identifiers, dates, actors, amounts and custom taxonomy slots.",
    "Use documents for file/type metadata and counts, and join document_promotions by document_id with is_current = 1 for direct document facts.",
    "Treat extracted_fields, extracted_rows, tags, people, organizations and documents_fts as normalized detail, recall and grouping layers.",
    "Treat document_payloads.normalized_json as the preferred raw payload layer.",
    "Treat document_payloads.structured_json as the structured fallback and audit layer.",
    "Treat source_documents/source_document_pages as deterministic multi-page document boundaries and structural_units/structural_unit_relations as the deterministic segmentation layer. base_unit and page_unit may be populated while chapter, section and page_span remain empty placeholders.",
    "For real page totals in page-wise corpora, count source_document_pages or structural_units where unit_type = 'page_unit'. Do not sum documents.page_count or documents.source_page_count, because they repeat the source-level page count on each page row.",
    "Treat evidence_atoms, slot_candidates and candidate_evidence as provenance tables for verification, not as the default source for direct document facts.",
    "When document_promotions, documents metadata and raw payloads disagree, prefer document_promotions for the working answer, then inspect normalized_json, structured_json and evidence.",
    "Do not assume every extracted_fields key is canonical. Some keys are structured fallback aliases kept for recall or compatibility."
  ].join("\n"),
  tool_routing: [
    "Tool routing:",
    "- Use sql_query on document_promotions for document-level facts and custom top-level slots; join documents for file/type metadata.",
    "- Use sql_query on documents for counts, file metadata, archive filters and coarse grouping.",
    "- Use sql_query on source_documents, source_document_pages, structural_units or structural_unit_relations when the answer depends on multi-page boundaries or deterministic segmentation.",
    "- For page totals use COUNT(*) from source_document_pages or COUNT(*) from structural_units WHERE unit_type = 'page_unit'.",
    "- Use sql_query on extracted_fields or extracted_rows when you need specific field keys or row content.",
    "- Use documents_fts MATCH for wording, recall and phrase-based retrieval.",
    "- Use semantic_search for thematic candidate generation only, then confirm with SQL or compact document views.",
    "- Use get_document_summary first for document identity and overview.",
    "- Use get_document_ontology_evidence for lens/evidence work, get_document_rows for tables or line items, and get_document_provenance for document-level evidence when the exact target slot is not known.",
    "- Use get_document_full/get_document only when compact document views are insufficient.",
    "- Use get_provenance when the user asks where a fact came from, whether a value is directly evidenced, or which layer produced a value.",
    "For FTS use only: documents_fts MATCH '...'. Do not use MATCH on documents_fts_content."
  ].join("\n"),
  workbench: [
    "Use workbench for small ad-hoc experiments, sqlite3 scripts, corpus file inspection, debugging and one-off analyses beyond the fixed tools.",
    "For workbench prefer compact JSON output.",
    "For Python workbench, MIN_AGENT_DB_PATH and MIN_AGENT_DATA_DIR point to the active user-selected corpus.",
    "For PowerShell workbench, stay strictly read-only and within approved active-corpus files under MIN_AGENT_DATA_DIR plus explicit config/soul files exposed by policy.",
    "Treat workbench as read-only analysis infrastructure, not as an editing surface.",
    "Never use destructive or write operations. If a runtime error suggests a missing bundled runtime, adapt your method instead of trying to force execution."
  ].join("\n"),
  answer_rules: [
    "If a tool returns an error, treat it as work feedback, repair the query or code, and retry when appropriate.",
    "When citing corpus evidence, write a short human-readable label and then an exact citation token: <file_name or title>, page <source_page> {{cite:doc:<page_level_document_id>}}.",
    "Use the page-level documents.id as <page_level_document_id>. In page-wise corpora, the file name alone is not a source because many pages can share the same file_name.",
    "Only create citation tokens for documents that were actually returned by tools in this turn. If you know only a file name or source_document_id, inspect source_document_pages, get_source_document, SQL or a compact get_document_* view first.",
    "Use citation tokens as the only machine-readable source link format.",
    "If the evidence is insufficient, say so plainly and explain what was insufficient.",
    "Do not invent schema, values, sources, dates or document ids.",
    "Rely on local database contents, local files and tool outputs only.",
    "This environment is local and read-only. Do not imply that you verified anything on the internet.",
    "You do not have a mandate to modify corpus data or local files while answering database questions.",
    "Do not expose chain-of-thought or hidden internal reasoning."
  ].join("\n")
};

export const DEFAULT_FRONTEND_POLICY = {
  chat_history: {
    max_history: 100,
    title_max_length: 80
  },
  memory: {
    max_summary_length: 150,
    max_topics: 6,
    max_search_results: 8,
    max_query_keys: 12,
    max_search_fetch: 64,
    recent_days_high: 7,
    recent_days_low: 30,
    filler_patterns: [
      regexDescriptor("^ich habe dazu ", "i"),
      regexDescriptor("^hier (sind|ist) ", "i"),
      regexDescriptor("^dazu habe ich ", "i"),
      regexDescriptor("^ich konnte ", "i"),
      regexDescriptor("^folgende ergebnisse gefunden[.!,]?\\s*", "i"),
      regexDescriptor("^ergebnisse gefunden[.!,]?\\s*", "i"),
      regexDescriptor("^basierend auf ", "i"),
      regexDescriptor("^laut den (daten|ergebnissen|informationen) ", "i"),
      regexDescriptor("^auf basis ", "i"),
      regexDescriptor("^gerne[.!,]?\\s", "i"),
      regexDescriptor("^selbstverstaendlich[.!,]?\\s", "i"),
      regexDescriptor("^natuerlich[.!,]?\\s", "i")
    ],
    query_stop_words: [
      "aber", "alle", "auch", "bitte", "danke", "das", "dass", "dem", "den", "der", "des", "diese", "diesem", "diesen",
      "dieser", "dieses", "dort", "du", "ein", "eine", "einem", "einen", "einer", "eines", "erinnern", "erinnerst",
      "frage", "gefragt", "gemeint", "gerade", "geredet", "gesagt", "gibt", "guten", "haben", "hallo", "hatte",
      "hatten", "hattest", "hier", "ich", "ihr", "ihnen", "ihre", "im", "in", "ist", "ja", "jetzt", "kann",
      "koennen", "konnen", "letzte", "letzten", "letztens", "mal", "mehr", "meinen", "mit", "muss", "noch", "nochmal",
      "nur", "oder", "praezisieren", "schon", "sehr", "sich", "sie", "sind", "soll", "ueber", "und", "uns", "unter",
      "vom", "von", "war", "waren", "was", "welche", "welchem", "welchen", "welcher", "welches", "wer", "wie",
      "wieviel", "wieviele", "wieder", "wir", "wird", "wurde", "zu", "zum", "zur", "besprochen"
    ],
    topic_stop_words: [
      "aktuell", "alle", "alles", "antwort", "auswertung", "bitte", "dabei", "danke", "das", "dazu", "der", "die",
      "diese", "dieser", "dieses", "durch", "ein", "eine", "frage", "fuer", "gibt", "gut", "haben", "hier", "ich",
      "ihnen", "ihre", "ist", "jede", "jetzt", "kann", "keine", "mach", "mehr", "nach", "nicht", "noch", "nur",
      "oder", "schon", "sehr", "sie", "sind", "soll", "summe", "ueber", "und", "unter", "war", "waren", "was",
      "welche", "welcher", "welches", "wer", "wie", "wird", "wurde", "zeig", "zwischen"
    ],
    non_memory_answer_patterns: [
      regexDescriptor("keine belastbare antwort formulieren", "i"),
      regexDescriptor("zu viele zwischenergebnisse erzeugt", "i"),
      regexDescriptor("bitte formulieren sie konkreter", "i"),
      regexDescriptor("bitte (praezisieren|konkretisieren)", "i"),
      regexDescriptor("ich konnte dazu nichts finden", "i"),
      regexDescriptor("ich habe dazu nichts gefunden", "i"),
      regexDescriptor("ich finde dazu nichts", "i"),
      regexDescriptor("kann ich nicht beantworten", "i"),
      regexDescriptor("ohne weitere angaben", "i"),
      regexDescriptor("(bitte|ich brauche).*(mehr kontext|mehr details)", "i")
    ]
  },
  model_catalog: {
    llm_seed_models: DEFAULT_LLM_SEED_MODELS,
    embedding_seed_models: [...providerCatalog.fallback_models.embedding_models],
    llm_source_order: [...SOURCE_ORDER_VALUES],
    embedding_source_order: [...SOURCE_ORDER_VALUES]
  },
  min_agent: {
    context: {
      history_context_ratio: 0.4,
      history_token_cap: 60_000,
      system_overhead_tokens: 1_300,
      average_turn_tokens: 450
    },
    runtime: {
      max_tool_rounds: 16,
      max_sql_rows: 50,
      max_text_length: 6_000,
      max_field_count: 120,
      max_evidence_count: 40,
      max_row_count: 25,
      max_workbench_output: 12_000,
      default_workbench_timeout_ms: 15_000
    },
    prompt: PROMPT_SECTIONS
  },
  ontology_agent: {
    prompt: ONTOLOGY_PROMPT_SECTIONS
  }
};

export function cloneFrontendPolicy() {
  return JSON.parse(JSON.stringify(DEFAULT_FRONTEND_POLICY));
}
