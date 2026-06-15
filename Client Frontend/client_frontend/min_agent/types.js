export const TOOL_DEFINITIONS = [
  {
    type: "function",
    function: {
      name: "sql_query",
      description:
        "Execute a single read-only SQLite SELECT or WITH query against corpus.db. Use document_promotions as the active top-level semantic fact surface for document titles, identifiers, dates, actors, amounts and custom taxonomy slots; join documents for file/type metadata and use source_documents/source_document_pages/structural_units for multi-page and segmentation structure. Use source_document_classifications for source-level base, semantic_release, and ontology-lens classifications. For real page totals, count source_document_pages or structural_units where unit_type = 'page_unit'; never sum documents.page_count or documents.source_page_count in page-wise corpora because those values repeat per page-level row. Use extracted_fields/extracted_rows for lower-level detail. Use document_payloads and evidence tables only for fallback, provenance or conflict resolution. Include id, file_name and source_page whenever you want sourceable documents or citation tokens. Do not present local file_path values to the user; use document id, title, file_name or corpus_ref instead.",
      parameters: {
        type: "object",
        properties: { query: { type: "string" } },
        required: ["query"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_document",
      description:
        "Load the full document inspection bundle across corpus layers. This is the expensive legacy/full view. Prefer get_document_summary, get_document_ontology_evidence, get_document_rows or get_document_provenance first, and use this only when compact views do not contain enough evidence.",
      parameters: {
        type: "object",
        properties: { doc_id: { type: "string" } },
        required: ["doc_id"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_document_summary",
      description:
        "Load a compact document identity and overview bundle: source, document metadata, source-document context, active document_promotions, structural hints and short excerpts. Use this as the first document read before escalating to heavier views.",
      parameters: {
        type: "object",
        properties: { doc_id: { type: "string" } },
        required: ["doc_id"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_document_ontology_evidence",
      description:
        "Load a compact ontology-facing evidence bundle for one document: source-document classifications, active promotions, selected fields, selected rows, structural units, evidence atoms and bounded payload excerpts. Use this for ontology lens design before considering the full document view.",
      parameters: {
        type: "object",
        properties: { doc_id: { type: "string" } },
        required: ["doc_id"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_document_rows",
      description:
        "Load a row-focused document view with extracted_rows, slot candidates, selected evidence atoms and compact excerpts. Use this for tables, line items, invoices, orders, shipments and row-level checks.",
      parameters: {
        type: "object",
        properties: { doc_id: { type: "string" } },
        required: ["doc_id"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_document_provenance",
      description:
        "Load a document-level provenance surface with promotions, fields, slot candidates, structural units and evidence atoms when the exact target slot is not known yet. For one known target, use get_provenance instead.",
      parameters: {
        type: "object",
        properties: { doc_id: { type: "string" } },
        required: ["doc_id"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_document_full",
      description:
        "Explicit full document read. Returns the same expensive full inspection bundle as get_document. Use only as a last escalation step after compact document views fail to answer the question.",
      parameters: {
        type: "object",
        properties: { doc_id: { type: "string" } },
        required: ["doc_id"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_provenance",
      description:
        "Load provenance for one document promotion slot, field or candidate slot. Returns active promotion facts, SQL field matches, slot candidates, linked evidence atoms, direct evidence hints and whether the result comes from document_promotions, normalized SQL or structured provenance. Use this when the user asks where a fact came from or whether it is directly evidenced.",
      parameters: {
        type: "object",
        properties: {
          doc_id: { type: "string" },
          target: { type: "string" },
          target_kind: { type: "string", enum: ["field", "slot", "promotion", "auto"] }
        },
        required: ["doc_id", "target"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "semantic_search",
      description:
        "Run semantic similarity search over embeddings built from document_promotions plus normalized document content. Prefer this for thematic similarity, paraphrases or fuzzy conceptual matches, then confirm exact facts with SQL or get_document. If embeddings are empty or unavailable, inspect the returned fallback results and continue with SQL/documents_fts keyword expansion instead of concluding that no documents exist.",
      parameters: {
        type: "object",
        properties: { text: { type: "string" }, limit: { type: "integer", minimum: 1, maximum: 20 } },
        required: ["text"],
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "database_coverage_snapshot",
      description:
        "Return a deterministic read-only coverage snapshot for the active corpus. Use this when the user asks how well the database is materialized, which semantic slots or fields dominate, where projections/promotions are weak, whether release materialization is mixed, or why the DB may feel like a black box. Page totals use source_document_pages or structural page_unit rows when available, not SUM(documents.page_count). This tool does not write reports or modify data; use its facts as evidence and then drill into SQL/get_document/get_provenance when needed.",
      parameters: {
        type: "object",
        properties: {
          focus: { type: "string", enum: ["overview", "promotions", "fields", "rows", "weak_spots", "release"] },
          limit: { type: "integer", minimum: 1, maximum: 100 }
        },
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_source_documents",
      description:
        "List deterministic source-document groups created from page-level documents by basic_relation_mining. Use this to understand multi-page documents, page counts and source-document boundaries before answering across pages. For finer deterministic segmentation, inspect structural_units and structural_unit_relations with sql_query.",
      parameters: {
        type: "object",
        properties: { limit: { type: "integer", minimum: 1, maximum: 100 } },
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_source_document",
      description:
        "Load one source-document group and its ordered page-level documents. Provide source_document_id or a page-level doc_id. Use this when a result is one page of a larger document.",
      parameters: {
        type: "object",
        properties: {
          source_document_id: { type: "string" },
          doc_id: { type: "string" },
          limit: { type: "integer", minimum: 1, maximum: 200 }
        },
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "list_ontology_lenses",
      description:
        "List ontology lenses available for the corpus, including the active primary lens and object counts. Ontology lenses are integral DB meaning, not optional metadata. Use this for database overviews, corpus summaries, comparisons, detail questions and interpretive answers when lenses may shape what the corpus means, even if the user did not explicitly ask for ontology.",
      parameters: {
        type: "object",
        properties: {
          include_archived: { type: "boolean" },
          limit: { type: "integer", minimum: 1, maximum: 100 }
        },
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_ontology_lens",
      description:
        "Load the active or selected ontology lens with representative nodes, edges and assertions. Use this to include ontology context in DB overviews, corpus summaries, comparisons, detail questions and interpretive answers. Treat the lens as interpretive DB context; still verify document facts through source-document or SQL evidence.",
      parameters: {
        type: "object",
        properties: {
          ontology_id: { type: "string" },
          limit: { type: "integer", minimum: 1, maximum: 200 }
        },
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "workbench",
      description:
        "General read-only local workbench. Use runtime='python' for ad-hoc sqlite3 analysis via MIN_AGENT_DB_PATH. Use runtime='powershell' only as a read-only corpus fallback for approved local files under the active corpus directory MIN_AGENT_DATA_DIR plus explicit config/soul files. Never use powershell for network access, UNC paths, process launch or generic shelling out. Do not use workbench as the default path for normal corpus lookup when sql_query or get_document are sufficient. Print compact JSON whenever possible. If documents matter, include doc_id/id or file_name values in the output so sources can be linked.",
      parameters: {
        type: "object",
        properties: {
          runtime: { type: "string", enum: ["python", "powershell"] },
          code: { type: "string" },
          timeout_ms: { type: "integer", minimum: 1000, maximum: 30000 }
        },
        required: ["runtime", "code"],
        additionalProperties: false
      }
    }
  }
];

export const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"];
export const MAX_TOOL_ROUNDS = 16;
export const MAX_SQL_ROWS = 50;
export const MAX_TEXT_LENGTH = 6_000;
export const MAX_FIELD_COUNT = 120;
export const MAX_EVIDENCE_COUNT = 40;
export const MAX_ROW_COUNT = 25;
export const MAX_WORKBENCH_OUTPUT = 12_000;
export const DEFAULT_WORKBENCH_TIMEOUT_MS = 15_000;
export const HISTORY_CONTEXT_RATIO = 0.4;
export const HISTORY_TOKEN_CAP = 60_000;
export const SYSTEM_OVERHEAD_TOKENS = 1_300;
export const AVERAGE_TURN_TOKENS = 450;
export const POWERSHELL_ALLOWED_ENV_VARS = new Set(["MIN_AGENT_ROOT_DIR", "MIN_AGENT_DATA_DIR", "MIN_AGENT_DB_PATH"]);
export const POWERSHELL_ALLOWED_COMMANDS = new Set([
  "Compare-Object",
  "ConvertFrom-Json",
  "ConvertTo-Json",
  "ForEach-Object",
  "Format-List",
  "Format-Table",
  "Get-ChildItem",
  "Get-Content",
  "Get-FileHash",
  "Get-Item",
  "Group-Object",
  "Join-Path",
  "Measure-Object",
  "Out-String",
  "Resolve-Path",
  "Select-Object",
  "Select-String",
  "Sort-Object",
  "Split-Path",
  "Test-Path",
  "Where-Object",
  "Write-Output"
]);
export const POWERSHELL_LANGUAGE_TOKENS = new Set([
  "begin",
  "break",
  "catch",
  "continue",
  "do",
  "else",
  "elseif",
  "end",
  "false",
  "filter",
  "finally",
  "for",
  "foreach",
  "function",
  "if",
  "in",
  "param",
  "process",
  "return",
  "switch",
  "throw",
  "trap",
  "true",
  "try",
  "while"
]);
