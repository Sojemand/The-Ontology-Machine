export const TABLE_KEY_CANDIDATES = new Map([
  ["ontology_lenses", ["ontology_id"]],
  ["ontology_runs", ["run_id"]],
  ["ontology_terms", ["term_id"]],
  ["ontology_nodes", ["node_id"]],
  ["ontology_edges", ["edge_id"]],
  ["ontology_assertions", ["assertion_id"]],
  ["ontology_evidence_links", ["evidence_link_id"]],
  ["ontology_activation", ["ontology_id"]],
  ["ontology_embedding_chunks", ["chunk_id"]],
  ["relations", ["id", "relation_id"]],
  ["documents", ["id"]],
  ["source_documents", ["source_document_id"]],
  ["source_document_classifications", ["source_document_id"]],
  ["structural_units", ["unit_id"]],
  ["evidence_atoms", ["atom_id"]],
  ["document_promotions", ["promotion_id"]],
  ["extracted_fields", ["id"]],
  ["extracted_rows", ["id"]],
  ["document_entities", ["entity_id", "id"]]
]);

export const REF_TARGETS = new Map([
  ["term", ["ontology_terms", ["term_id"], true]],
  ["node", ["ontology_nodes", ["node_id"], true]],
  ["edge", ["ontology_edges", ["edge_id"], true]],
  ["assertion", ["ontology_assertions", ["assertion_id"], true]],
  ["relation", ["relations", ["id", "relation_id"], false]],
  ["document", ["documents", ["id"], false]],
  ["page", ["documents", ["id"], false]],
  ["source_document", ["source_documents", ["source_document_id"], false]],
  ["structural_unit", ["structural_units", ["unit_id"], false]],
  ["evidence_atom", ["evidence_atoms", ["atom_id"], false]],
  ["promotion", ["document_promotions", ["promotion_id"], false]],
  ["field", ["extracted_fields", ["id"], false]],
  ["row", ["extracted_rows", ["id"], false]],
  ["entity", ["document_entities", ["entity_id", "id"], false]]
]);

export const EVIDENCE_TARGETS = new Map([
  ["term", ["ontology_terms", ["term_id"], true]],
  ["node", ["ontology_nodes", ["node_id"], true]],
  ["edge", ["ontology_edges", ["edge_id"], true]],
  ["assertion", ["ontology_assertions", ["assertion_id"], true]],
  ["relation", ["relations", ["id", "relation_id"], false]]
]);

export const EMBEDDING_TARGETS = new Map([
  ["term", ["ontology_terms", ["term_id"], true]],
  ["node", ["ontology_nodes", ["node_id"], true]],
  ["edge", ["ontology_edges", ["edge_id"], true]],
  ["assertion", ["ontology_assertions", ["assertion_id"], true]],
  ["lens", ["ontology_lenses", ["ontology_id"], false]]
]);

export function fetchTargetRow(database, tableName, keyCandidates, refId) {
  const tableInfo = getTableInfo(database, tableName);
  if (!tableInfo.exists) return null;
  const key = keyCandidates.find((candidate) => tableInfo.columns.has(candidate));
  if (!key) return null;
  try {
    return database.prepare(`SELECT * FROM ${tableName} WHERE ${key} = ? LIMIT 1`).get(String(refId));
  } catch {
    return null;
  }
}

export function getTableInfo(database, tableName) {
  try {
    const rows = database.prepare(`PRAGMA table_info(${tableName})`).all();
    return {
      exists: rows.length > 0,
      rows,
      columns: new Set(rows.map((row) => String(row.name || "")))
    };
  } catch {
    return { exists: false, rows: [], columns: new Set() };
  }
}
