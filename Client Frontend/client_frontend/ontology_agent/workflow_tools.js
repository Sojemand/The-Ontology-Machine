import { resolveMinAgentRuntimePolicy } from "../frontend_policy.js";
import { buildSqlErrorResult } from "../min_agent/query_repository.js";
import { extractDocIdsFromRows } from "../min_agent/source_domain.js";

function parseToolArguments(toolCall) {
  try {
    return JSON.parse(toolCall?.function?.arguments || "{}");
  } catch {
    return null;
  }
}

export function docIdsFromToolResult(result) {
  const ids = new Set();
  const appendRows = (rows) => {
    for (const docId of extractDocIdsFromRows(rows)) ids.add(docId);
  };
  appendRows(result?.rows);
  appendRows(result?.results);
  appendRows(result?.fallback?.rows);
  appendRows(result?.fallback?.results);
  appendRows(result?.pages?.rows);
  if (result?.source?.id) ids.add(result.source.id);
  if (Array.isArray(result?.sources)) {
    for (const source of result.sources) if (source?.id) ids.add(source.id);
  }
  return [...ids];
}

export async function executeOntologyToolCall(toolCall, options) {
  const args = parseToolArguments(toolCall);
  if (!args) return { ok: false, error: "Tool arguments could not be read." };
  const handler = createToolHandlers(args, options)[toolCall?.function?.name];
  return handler ? await handler() : { ok: false, error: `Unknown tool: ${toolCall?.function?.name}` };
}

function createToolHandlers(args, options) {
  const {
    repository,
    readFrontendPolicy,
    readRuntimeConfig,
    embedTextsFn,
    runBasicRelationMiningFn,
    pipelineRoot,
    dbPath,
    stateRoot
  } = options;
  const runtimePolicy = resolveMinAgentRuntimePolicy(readFrontendPolicy());
  return {
    sql_query: () => safeSqlQuery(repository, args, runtimePolicy),
    get_document: () => safeGetDocument(repository, args, runtimePolicy),
    get_document_summary: () => safeGetDocumentView(repository, args, runtimePolicy, "getDocumentSummary", "get_document_summary"),
    get_document_ontology_evidence: () => safeGetDocumentView(repository, args, runtimePolicy, "getDocumentOntologyEvidence", "get_document_ontology_evidence"),
    get_document_rows: () => safeGetDocumentView(repository, args, runtimePolicy, "getDocumentRows", "get_document_rows"),
    get_document_provenance: () => safeGetDocumentView(repository, args, runtimePolicy, "getDocumentProvenance", "get_document_provenance"),
    get_document_full: () => safeGetDocumentView(repository, args, runtimePolicy, "getDocumentFull", "get_document_full"),
    get_provenance: () => safeGetProvenance(repository, args, runtimePolicy),
    semantic_search: () => semanticSearch(repository, args, { readRuntimeConfig, embedTextsFn }),
    database_coverage_snapshot: () => repository.databaseCoverageSnapshot(args),
    list_source_documents: () => repository.listSourceDocuments(args),
    get_source_document: () => repository.getSourceDocument(args),
    list_ontology_lenses: () => repository.listOntologyLenses(args),
    get_ontology_lens: () => repository.getOntologyLens(args),
    basic_relation_mining: () => runBasicRelationMiningFn({
      pipelineRoot,
      dbPath,
      stateRoot,
      dryRun: Boolean(args.dry_run)
    }),
    sql_batch_execute: () => repository.sqlBatchExecute(args)
  };
}

function safeSqlQuery(repository, args, runtimePolicy) {
  try {
    return repository.sqlQuery(args.query, runtimePolicy);
  } catch (error) {
    return buildSqlErrorResult(error, args.query, repository.schemaSummary);
  }
}

function safeGetDocument(repository, args, runtimePolicy) {
  try {
    return repository.getDocument(args.doc_id, runtimePolicy);
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "get_document failed.", doc_id: args.doc_id };
  }
}

function safeGetDocumentView(repository, args, runtimePolicy, methodName, toolName) {
  try {
    return repository[methodName](args.doc_id, runtimePolicy);
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : `${toolName} failed.`, doc_id: args.doc_id };
  }
}

function safeGetProvenance(repository, args, runtimePolicy) {
  try {
    return repository.getProvenance(args.doc_id, args.target, args.target_kind, runtimePolicy);
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "get_provenance failed.", doc_id: args.doc_id, target: args.target };
  }
}

async function semanticSearch(repository, args, { readRuntimeConfig, embedTextsFn }) {
  const activeRuntimeConfig = readRuntimeConfig();
  const indexState = repository.semanticIndexState();
  if (!indexState.available) {
    return {
      ...indexState,
      fallback: repository.keywordSearch(args.text, args.limit)
    };
  }
  try {
    const [queryVector] = await embedTextsFn(activeRuntimeConfig, [args.text]);
    return repository.semanticSearch(Float32Array.from(queryVector), args.limit);
  } catch (error) {
    return {
      available: false,
      error: error instanceof Error ? error.message : "semantic_search failed.",
      results: [],
      fallback: repository.keywordSearch(args.text, args.limit)
    };
  }
}
