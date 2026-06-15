import { TOOL_DEFINITIONS } from "../min_agent/types.js";

const ONTOLOGY_READ_TOOL_NAMES = new Set([
  "sql_query",
  "get_document",
  "get_document_summary",
  "get_document_ontology_evidence",
  "get_document_rows",
  "get_document_provenance",
  "get_document_full",
  "get_provenance",
  "semantic_search",
  "database_coverage_snapshot",
  "list_source_documents",
  "get_source_document",
  "list_ontology_lenses",
  "get_ontology_lens"
]);

const SQL_BATCH_EXECUTE_DESCRIPTION = [
  "Execute an atomic batch of ontology-layer SQLite writes against the active corpus DB.",
  "Use this to create or update ontology lenses, terms, nodes, edges, assertions, evidence links, run checkpoints and activation state.",
  "It may also write ontology-scoped source_document_classifications; base and semantic_release classification rows are deterministic Base Graph materialization and should not be overwritten by the agent.",
  "The tool enforces the write allowlist, writes ontology_edit_log, runs deterministic validation and refreshes ontology embeddings when possible.",
  "Never include a database path.",
  "Required insert contract: every INSERT/REPLACE must use an explicit column list and explicit VALUES. Do not rely on implicit rowid, defaults, AUTOINCREMENT assumptions, or omitted primary IDs.",
  "Required stable IDs/fields by table: ontology_lenses: ontology_id; ontology_runs: run_id, ontology_id; ontology_terms: term_id, ontology_id; ontology_nodes: node_id, ontology_id; ontology_edges: edge_id, ontology_id, source_node_id, target_node_id; ontology_assertions: assertion_id, ontology_id; ontology_evidence_links: evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id; ontology_activation: ontology_id; ontology_embedding_chunks: chunk_id, ontology_id, object_type, object_id.",
  "ID rule: all required IDs must be explicit non-empty strings. Never use NULL, empty string, rowid, or omitted primary-key fields. Prefer deterministic IDs from semantic inputs, for example ev_<short_hash> for evidence links.",
  "Write rows parent-first: lens before objects using ontology_id, nodes before edges, runs before run_id references, targets before evidence links.",
  "Object model: ontology_terms are vocabulary; ontology_nodes are graph objects and the only valid ontology_edges endpoints; ontology_assertions are claims; ontology_evidence_links attach provenance.",
  "Source-document classification model: classification_scope='ontology' must include ontology_id; classification_scope='base' or 'semantic_release' must omit ontology_id.",
  "JSON rule: when providing JSON columns, provide valid explicit JSON values such as '{}' for attributes_json/intent_json/policy_json and '[]' for aliases_json.",
  "Evidence links: create them only after the target object exists. target_type must be one of term, node, edge, assertion, relation. evidence_ref_type must be one of document, source_document, structural_unit, evidence_atom, promotion, field, row. evidence_ref_id must point to an existing object of that type.",
  "ontology_lenses.status accepts draft, ready or archived only; active/primary state belongs in ontology_activation.",
  "Preflight: before opening a transaction, the tool checks columns, required values, parent rows, same-lens references, node-to-node edge endpoints, evidence targets and embedding object references.",
  "Repair loop: if the tool returns error_type='ontology_write_preflight' with repairable=true, repair internally in the current call by reading schema/IDs if needed and issuing a corrected sql_batch_execute. Do not ask the user unless the repair budget is exhausted.",
  "Failure handling: if post-write validation fails, do not continue writing new ontology content. Inspect the validation error, repair the exact broken rows first, then rerun validation and embedding refresh."
].join(" ");

const BASIC_RELATION_MINING_DESCRIPTION = [
  "Run the deterministic Base Graph/source-document/structural-unit construction on the active Query Agent corpus DB from the current frontend config.",
  "Use this when the user asks to start base DB construction, Base Graph construction, source-document grouping, structural segmentation scaffolding, or when source_documents/source_document_pages/structural_units are missing.",
  "This tool never accepts a database path.",
  "After it has run, real page totals should be counted from source_document_pages or structural_units where unit_type = 'page_unit', not by summing documents.page_count/source_page_count."
].join(" ");

export const ONTOLOGY_TOOL_DEFINITIONS = [
  ...TOOL_DEFINITIONS.filter((tool) => ONTOLOGY_READ_TOOL_NAMES.has(tool?.function?.name)),
  {
    type: "function",
    function: {
      name: "basic_relation_mining",
      description: BASIC_RELATION_MINING_DESCRIPTION,
      parameters: {
        type: "object",
        properties: {
          dry_run: {
            type: "boolean",
            description: "If true, inspect what would be built without writing. Default false for explicit user requests to start construction."
          }
        },
        additionalProperties: false
      }
    }
  },
  {
    type: "function",
    function: {
      name: "sql_batch_execute",
      description: SQL_BATCH_EXECUTE_DESCRIPTION,
      parameters: {
        type: "object",
        properties: {
          edit_summary: { type: "string" },
          ontology_id: { type: "string" },
          statements: {
            type: "array",
            minItems: 1,
            maxItems: 50,
            items: {
              type: "object",
              properties: {
                sql: { type: "string" },
                params: { type: "array", items: {} }
              },
              required: ["sql"],
              additionalProperties: false
            }
          }
        },
        required: ["statements"],
        additionalProperties: false
      }
    }
  }
];

export const ONTOLOGY_MAX_TOOL_ROUNDS = 32;
