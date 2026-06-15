import {
  EMBEDDING_TARGETS,
  EVIDENCE_TARGETS,
  REF_TARGETS,
  TABLE_KEY_CANDIDATES,
  fetchTargetRow
} from "./write_preflight_schema.js";
import { addError } from "./write_preflight_report.js";
import { stringValue } from "./write_preflight_sql.js";

export function validateInsertReferences(state, tableName, parsed, index) {
  const value = (column) => stringValue(parsed.valuesByColumn.get(column));
  const ontologyId = value("ontology_id") || state.ontologyId;
  if (tableName !== "ontology_lenses" && tableName.startsWith("ontology_") && tableName !== "ontology_edit_log") {
    requireReference(state, index, tableName, {
      sourceColumn: "ontology_id",
      refType: "lens",
      targetTable: "ontology_lenses",
      keyCandidates: ["ontology_id"],
      refId: ontologyId,
      repair: "Insert or update ontology_lenses before writing rows that reference ontology_id."
    });
  }
  if (tableName === "ontology_runs") return;
  if (tableName === "source_document_classifications") return validateSourceDocumentClassification(state, tableName, value, index);
  if (tableName === "ontology_edges") return validateOntologyEdges(state, tableName, value, index, ontologyId);
  if (tableName === "ontology_assertions") return validateOntologyAssertions(state, tableName, value, index, ontologyId);
  if (tableName === "ontology_evidence_links") return validateEvidenceLinks(state, tableName, value, index, ontologyId);
  if (tableName === "ontology_embedding_chunks") {
    requireMappedRef(state, index, tableName, "object_type", value("object_type"), "object_id", value("object_id"), ontologyId, EMBEDDING_TARGETS, "Create the ontology object before inserting embedding chunks.");
  }
}

export function registerCreatedRow(state, tableName, parsed) {
  const keyColumn = firstPresent(parsed.valuesByColumn, TABLE_KEY_CANDIDATES.get(tableName) || []);
  if (!keyColumn) return;
  const keyValue = stringValue(parsed.valuesByColumn.get(keyColumn));
  if (!keyValue) return;
  if (!state.created.has(tableName)) state.created.set(tableName, new Map());
  state.created.get(tableName).set(keyValue, Object.fromEntries(
    Array.from(parsed.valuesByColumn.entries()).map(([column, value]) => [column, value.known ? value.value : null])
  ));
}

function validateSourceDocumentClassification(state, tableName, value, index) {
  requireReference(state, index, tableName, {
    sourceColumn: "source_document_id",
    refType: "source_document",
    targetTable: "source_documents",
    keyCandidates: ["source_document_id"],
    refId: value("source_document_id"),
    repair: "Use an existing source_documents.source_document_id."
  });
  if (value("classification_scope") !== "ontology") {
    addError(state, "source_document_classification_scope_not_agent_writable", index, tableName, `${tableName}.classification_scope='${value("classification_scope")}' is deterministic materialization, not an Ontology Agent write scope.`, "Use classification_scope='ontology' with ontology_id for agent-authored source document classifications. Leave base/semantic_release rows to basic_relation_mining.");
    return;
  }
  requireReference(state, index, tableName, {
    sourceColumn: "ontology_id",
    refType: "lens",
    targetTable: "ontology_lenses",
    keyCandidates: ["ontology_id"],
    refId: value("ontology_id"),
    repair: "Ontology-scoped source_document_classifications must reference an existing ontology_lenses.ontology_id."
  });
}

function validateOntologyEdges(state, tableName, value, index, ontologyId) {
  requireReference(state, index, tableName, {
    sourceColumn: "source_node_id",
    refType: "node",
    targetTable: "ontology_nodes",
    keyCandidates: ["node_id"],
    refId: value("source_node_id"),
    ontologyId,
    sameOntology: true,
    repair: "Create the source ontology_node before inserting the edge. Edges are node-to-node only."
  });
  requireReference(state, index, tableName, {
    sourceColumn: "target_node_id",
    refType: "node",
    targetTable: "ontology_nodes",
    keyCandidates: ["node_id"],
    refId: value("target_node_id"),
    ontologyId,
    sameOntology: true,
    repair: "Create the target ontology_node before inserting the edge. Do not use ontology_terms.term_id as an edge endpoint."
  });
}

function validateOntologyAssertions(state, tableName, value, index, ontologyId) {
  requireSemanticRef(state, index, tableName, "subject_ref_type", value("subject_ref_type"), "subject_ref_id", value("subject_ref_id"), ontologyId, true);
  const objectType = value("object_ref_type");
  const objectId = value("object_ref_id");
  if (objectType || objectId) {
    requireSemanticRef(state, index, tableName, "object_ref_type", objectType, "object_ref_id", objectId, ontologyId, true);
  }
}

function validateEvidenceLinks(state, tableName, value, index, ontologyId) {
  requireMappedRef(state, index, tableName, "target_type", value("target_type"), "target_id", value("target_id"), ontologyId, EVIDENCE_TARGETS, "Create the evidence target object before inserting ontology_evidence_links.");
  requireMappedRef(state, index, tableName, "evidence_ref_type", value("evidence_ref_type"), "evidence_ref_id", value("evidence_ref_id"), ontologyId, REF_TARGETS, "Use an existing document, source_document, structural_unit, evidence_atom, promotion, field, row or entity as evidence.");
  const runId = value("run_id");
  if (runId) {
    requireReference(state, index, tableName, {
      sourceColumn: "run_id",
      refType: "run",
      targetTable: "ontology_runs",
      keyCandidates: ["run_id"],
      refId: runId,
      repair: "Create ontology_runs first or omit run_id."
    });
  }
}

function requireSemanticRef(state, index, tableName, typeColumn, refType, idColumn, refId, ontologyId, required) {
  if (!refType || !refId) {
    if (required) addError(state, "incomplete_ref", index, tableName, `${tableName}.${typeColumn}/${idColumn} must both be provided.`, "Provide a complete semantic reference pair.");
    return;
  }
  requireMappedRef(state, index, tableName, typeColumn, refType, idColumn, refId, ontologyId, REF_TARGETS, "Use a valid existing semantic reference target.");
}

function requireMappedRef(state, index, tableName, typeColumn, refType, idColumn, refId, ontologyId, targetMap, repair) {
  const target = targetMap.get(String(refType || ""));
  if (!target) {
    addError(state, "unknown_ref_type", index, tableName, `${tableName}.${typeColumn}='${refType}' is not a known reference type.`, repair);
    return;
  }
  const [targetTable, keyCandidates, sameOntology] = target;
  requireReference(state, index, tableName, { sourceColumn: idColumn, refType, targetTable, keyCandidates, refId, ontologyId, sameOntology, repair });
}

function requireReference(state, index, tableName, { sourceColumn, refType, targetTable, keyCandidates, refId, ontologyId = "", sameOntology = false, repair }) {
  if (!refId) {
    addError(state, "missing_ref_id", index, tableName, `${tableName}.${sourceColumn} is missing for ${refType} reference.`, repair);
    return;
  }
  const created = getCreatedRow(state, targetTable, refId);
  if (created) return validateSameOntology(state, index, tableName, sourceColumn, refId, targetTable, created.ontology_id, ontologyId, sameOntology);
  const row = fetchTargetRow(state.database, targetTable, keyCandidates, refId);
  if (row) return validateSameOntology(state, index, tableName, sourceColumn, refId, targetTable, row.ontology_id, ontologyId, sameOntology);
  const termRow = targetTable === "ontology_nodes" ? fetchTargetRow(state.database, "ontology_terms", ["term_id"], refId) : null;
  addError(
    state,
    termRow ? "term_used_as_node" : "missing_ref_target",
    index,
    tableName,
    termRow
      ? `${tableName}.${sourceColumn}='${refId}' is an ontology_term, but ${tableName} requires an ontology_node endpoint.`
      : `${tableName}.${sourceColumn}='${refId}' does not reference an existing or earlier-created ${targetTable} row.`,
    termRow ? "Create a dedicated ontology_node for that term/value first, then point the edge at node_id." : repair
  );
}

function validateSameOntology(state, index, tableName, sourceColumn, refId, targetTable, targetOntologyId, ontologyId, sameOntology) {
  if (sameOntology && ontologyId && targetOntologyId && String(targetOntologyId) !== String(ontologyId)) {
    addError(state, "same_ontology_ref_mismatch", index, tableName, `${tableName}.${sourceColumn}='${refId}' points to ${targetTable} in ontology '${targetOntologyId}', not '${ontologyId}'.`, "Use a target from the same ontology lens.");
  }
}

function getCreatedRow(state, tableName, id) {
  return state.created.get(tableName)?.get(String(id || "")) || null;
}

function firstPresent(valuesByColumn, candidates) {
  return candidates.find((candidate) => valuesByColumn.has(candidate)) || "";
}
