import { collectCappedRows } from "./sql_policy.js";
import { MAX_SQL_ROWS } from "./types.js";
import { getAvailableColumns, tableExists } from "./corpus_tables.js";

export function createOntologyReadRepository({ database }) {
  function unavailable(reason) {
    return { available: false, reason, rows: [], row_count: 0, truncated: false };
  }

  function requireTable(tableName) {
    return tableExists(database, tableName);
  }

  function countRows(tableName, whereSql = "") {
    if (!requireTable(tableName)) return 0;
    return Number(database.prepare(`SELECT COUNT(*) AS count FROM ${tableName}${whereSql}`).get()?.count) || 0;
  }

  function structuralUnitCounts() {
    if (!requireTable("structural_units")) return { total: 0, base_units: 0, page_units: 0 };
    const unitTypeColumns = getAvailableColumns(database, "structural_units", ["unit_type"]);
    if (!unitTypeColumns.length) return { total: countRows("structural_units"), base_units: 0, page_units: 0 };
    const rows = database.prepare(
      "SELECT unit_type, COUNT(*) AS count FROM structural_units GROUP BY unit_type"
    ).all();
    const counts = Object.fromEntries(rows.map((row) => [String(row.unit_type || ""), Number(row.count) || 0]));
    return {
      total: countRows("structural_units"),
      base_units: counts.base_unit || 0,
      page_units: counts.page_unit || 0
    };
  }

  function baseRelationCount() {
    if (!requireTable("relations")) return 0;
    return getAvailableColumns(database, "relations", ["relation_origin"]).length
      ? countRows("relations", " WHERE relation_origin = 'base_graph'")
      : countRows("relations");
  }

  function activeDocumentWhere(alias = "") {
    if (!requireTable("documents")) return "";
    const prefix = alias ? `${alias}.` : "";
    return getAvailableColumns(database, "documents", ["is_archived"]).length
      ? ` WHERE COALESCE(${prefix}is_archived, 0) = 0`
      : "";
  }

  function activeDocumentCount() {
    if (!requireTable("documents")) return 0;
    return countRows("documents", activeDocumentWhere());
  }

  function unmappedSourceDocumentPageCount() {
    if (!requireTable("documents") || !requireTable("source_document_pages")) return 0;
    const pageColumns = getAvailableColumns(database, "source_document_pages", ["document_id"]);
    if (!pageColumns.includes("document_id")) return 0;
    const archivedClause = activeDocumentWhere("d").replace(/^ WHERE /, " AND ");
    const row = database.prepare(
      "SELECT COUNT(*) AS count FROM documents d "
      + "LEFT JOIN source_document_pages sdp ON sdp.document_id = d.id "
      + `WHERE sdp.document_id IS NULL${archivedClause}`
    ).get();
    return Number(row?.count) || 0;
  }

  function ontologyLensStatus() {
    if (!requireTable("ontology_lenses")) {
      return { available: false, count: 0, active_count: 0, primary_ontology_id: null };
    }
    const count = countRows("ontology_lenses");
    const activationColumns = requireTable("ontology_activation")
      ? getAvailableColumns(database, "ontology_activation", ["ontology_id", "is_active", "is_primary", "activated_at"])
      : [];
    const hasActivationState = activationColumns.includes("ontology_id") && activationColumns.includes("is_active");
    const activeCount = hasActivationState
      ? Number(database.prepare("SELECT COUNT(DISTINCT ontology_id) AS count FROM ontology_activation WHERE is_active = 1").get()?.count) || 0
      : 0;
    const hasPrimaryState = hasActivationState && activationColumns.includes("is_primary");
    const orderBy = activationColumns.includes("activated_at") ? " ORDER BY activated_at DESC" : "";
    const primary = hasPrimaryState
      ? database.prepare(`SELECT ontology_id FROM ontology_activation WHERE is_active = 1 AND is_primary = 1${orderBy} LIMIT 1`).get()
      : null;
    return {
      available: true,
      count,
      active_count: activeCount,
      primary_ontology_id: primary?.ontology_id ? String(primary.ontology_id) : null
    };
  }

  function databaseStructureStatus() {
    const documentCount = activeDocumentCount();
    const unmappedDocumentCount = unmappedSourceDocumentPageCount();
    const sourceDocumentCount = countRows("source_documents");
    const sourcePageCount = countRows("source_document_pages");
    const structuralUnits = structuralUnitCounts();
    const hasSourceDocumentGraph = sourceDocumentCount > 0 && sourcePageCount > 0;
    const hasStructuralGraph = structuralUnits.base_units > 0 && structuralUnits.page_units > 0;
    const baseGraphAvailable = hasSourceDocumentGraph || hasStructuralGraph;
    return {
      base_graph: {
        available: baseGraphAvailable,
        dirty: baseGraphAvailable && unmappedDocumentCount > 0,
        document_count: documentCount,
        unmapped_document_count: unmappedDocumentCount,
        source_document_count: sourceDocumentCount,
        source_page_count: sourcePageCount,
        structural_unit_count: structuralUnits.total,
        base_unit_count: structuralUnits.base_units,
        page_unit_count: structuralUnits.page_units,
        relation_count: baseRelationCount()
      },
      ontology_lenses: ontologyLensStatus()
    };
  }

  function listSourceDocuments({ limit = 25 } = {}) {
    if (!requireTable("source_documents") || !requireTable("source_document_pages")) {
      return unavailable("source_documents/source_document_pages are not materialized. Run basic_relation_mining first.");
    }
    const normalizedLimit = Math.min(100, Math.max(1, Number(limit) || 25));
    const statement = database.prepare(
      "SELECT sd.source_document_id, sd.source_uri, sd.source_title, sd.source_kind, sd.page_count, "
      + "sd.first_document_id, sd.last_document_id, sd.updated_at, "
      + "COUNT(sdp.document_id) AS materialized_pages "
      + "FROM source_documents sd LEFT JOIN source_document_pages sdp ON sdp.source_document_id = sd.source_document_id "
      + "GROUP BY sd.source_document_id ORDER BY sd.source_document_id LIMIT ?"
    );
    return { available: true, ...collectCappedRows(statement, [normalizedLimit], normalizedLimit) };
  }

  function getSourceDocument({ source_document_id: sourceDocumentId = "", doc_id: docId = "", limit = 50 } = {}) {
    if (!requireTable("source_documents") || !requireTable("source_document_pages")) {
      return unavailable("source_documents/source_document_pages are not materialized. Run basic_relation_mining first.");
    }
    const normalizedLimit = Math.min(200, Math.max(1, Number(limit) || 50));
    let resolvedId = String(sourceDocumentId || "").trim();
    if (!resolvedId && docId) {
      const row = database.prepare("SELECT source_document_id FROM source_document_pages WHERE document_id = ?").get(String(docId));
      resolvedId = String(row?.source_document_id || "");
    }
    if (!resolvedId) return { available: false, reason: "source_document_id or doc_id is required.", source_document: null, pages: [] };
    const source = database.prepare("SELECT * FROM source_documents WHERE source_document_id = ?").get(resolvedId) || null;
    const pages = collectCappedRows(
      database.prepare(
        "SELECT sdp.source_document_id, sdp.document_id AS id, sdp.page_index, sdp.page_label, "
        + "sdp.prev_document_id, sdp.next_document_id, d.file_name, d.document_type, d.category, d.content_free_text "
        + "FROM source_document_pages sdp JOIN documents d ON d.id = sdp.document_id "
        + "WHERE sdp.source_document_id = ? ORDER BY sdp.page_index, sdp.document_id"
      ),
      [resolvedId],
      normalizedLimit
    );
    const classifications = requireTable("source_document_classifications")
      ? collectCappedRows(
          database.prepare(
            "SELECT source_document_id, classification_scope, ontology_id, document_type, category, subcategory, "
            + "confidence, status, created_by, basis_json "
            + "FROM source_document_classifications WHERE source_document_id = ? "
            + "ORDER BY classification_scope, ontology_id LIMIT ?"
          ),
          [resolvedId, normalizedLimit],
          normalizedLimit
        )
      : { rows: [], row_count: 0, truncated: false };
    return { available: Boolean(source), source_document: source, classifications, ...pages };
  }

  function listOntologyLenses({ include_archived: includeArchived = false, limit = 50 } = {}) {
    if (!requireTable("ontology_lenses")) return unavailable("ontology_lenses table is not available.");
    const normalizedLimit = Math.min(100, Math.max(1, Number(limit) || 50));
    const where = includeArchived ? "" : "WHERE lens.status != 'archived'";
    const statement = database.prepare(
      "SELECT lens.ontology_id, lens.name, lens.description, lens.status, lens.parent_ontology_id, "
      + "lens.embedding_status, lens.embedding_error, lens.updated_at, "
      + "COALESCE(active.is_active, 0) AS is_active, COALESCE(active.is_primary, 0) AS is_primary, "
      + "(SELECT COUNT(*) FROM ontology_nodes node WHERE node.ontology_id = lens.ontology_id) AS node_count, "
      + "(SELECT COUNT(*) FROM ontology_edges edge WHERE edge.ontology_id = lens.ontology_id) AS edge_count, "
      + "(SELECT COUNT(*) FROM ontology_assertions assertion WHERE assertion.ontology_id = lens.ontology_id) AS assertion_count "
      + "FROM ontology_lenses lens LEFT JOIN ontology_activation active ON active.ontology_id = lens.ontology_id "
      + `${where} ORDER BY active.is_primary DESC, active.is_active DESC, lens.updated_at DESC, lens.created_at DESC LIMIT ?`
    );
    return { available: true, ...collectCappedRows(statement, [normalizedLimit], normalizedLimit) };
  }

  function getOntologyLens({ ontology_id: ontologyId = "", limit = 50 } = {}) {
    if (!requireTable("ontology_lenses")) return unavailable("ontology_lenses table is not available.");
    const normalizedLimit = Math.min(200, Math.max(1, Number(limit) || 50));
    const resolvedId = String(ontologyId || "").trim() || activeOntologyId();
    if (!resolvedId) return { available: false, reason: "No ontology_id was supplied and no primary lens is active.", lens: null };
    const lens = database.prepare("SELECT * FROM ontology_lenses WHERE ontology_id = ?").get(resolvedId) || null;
    const nodes = requireTable("ontology_nodes")
      ? collectCappedRows(database.prepare("SELECT * FROM ontology_nodes WHERE ontology_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT ?"), [resolvedId, normalizedLimit], normalizedLimit)
      : { rows: [], row_count: 0, truncated: false };
    const edges = requireTable("ontology_edges")
      ? collectCappedRows(database.prepare("SELECT * FROM ontology_edges WHERE ontology_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT ?"), [resolvedId, normalizedLimit], normalizedLimit)
      : { rows: [], row_count: 0, truncated: false };
    const assertions = requireTable("ontology_assertions")
      ? collectCappedRows(database.prepare("SELECT * FROM ontology_assertions WHERE ontology_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT ?"), [resolvedId, normalizedLimit], normalizedLimit)
      : { rows: [], row_count: 0, truncated: false };
    return { available: Boolean(lens), ontology_id: resolvedId, lens, nodes, edges, assertions };
  }

  function activeOntologyId() {
    if (!requireTable("ontology_activation")) return "";
    const activationColumns = getAvailableColumns(database, "ontology_activation", ["ontology_id", "is_active", "is_primary", "activated_at"]);
    if (!activationColumns.includes("ontology_id") || !activationColumns.includes("is_active") || !activationColumns.includes("is_primary")) return "";
    const orderBy = activationColumns.includes("activated_at") ? " ORDER BY activated_at DESC" : "";
    const row = database.prepare(
      `SELECT ontology_id FROM ontology_activation WHERE is_active = 1 AND is_primary = 1${orderBy} LIMIT 1`
    ).get();
    return String(row?.ontology_id || "");
  }

  return {
    listSourceDocuments,
    getSourceDocument,
    listOntologyLenses,
    getOntologyLens,
    activeOntologyId,
    databaseStructureStatus,
    ontologyReadState() {
      return {
        source_documents_available: requireTable("source_documents") && requireTable("source_document_pages"),
        structural_units_available: requireTable("structural_units") && requireTable("structural_unit_relations"),
        ontology_lenses_available: requireTable("ontology_lenses"),
        active_ontology_id: activeOntologyId()
      };
    }
  };
}
