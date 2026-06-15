import { randomUUID } from "node:crypto";

function vectorToBuffer(vector) {
  return Buffer.from(Float32Array.from(vector).buffer);
}

function present(value) {
  return String(value || "").trim();
}

function pushChunk(chunks, skipped, tableName, idColumn, row, buildChunk) {
  const objectId = present(row?.[idColumn]);
  if (!objectId) {
    skipped.push({ table: tableName, id_column: idColumn, rowid: row?.rowid || null });
    return;
  }
  chunks.push(buildChunk(objectId));
}

function ontologyObjects(database, ontologyId) {
  const chunks = [];
  const skipped = [];
  const lens = database.prepare("SELECT rowid, ontology_id, name, description, intent_json FROM ontology_lenses WHERE ontology_id = ?").get(ontologyId);
  if (lens) {
    pushChunk(chunks, skipped, "ontology_lenses", "ontology_id", lens, (objectId) => ({
      object_type: "lens",
      object_id: objectId,
      chunk_type: "ontology_lens",
      source_kind: "ontology_lenses",
      source_refs_json: JSON.stringify([{ table: "ontology_lenses", id: objectId }]),
      chunk_text: [lens.name, lens.description, lens.intent_json].filter(Boolean).join("\n")
    }));
  }
  for (const row of database.prepare("SELECT rowid, term_id, label, term_kind, definition, aliases_json FROM ontology_terms WHERE ontology_id = ?").all(ontologyId)) {
    pushChunk(chunks, skipped, "ontology_terms", "term_id", row, (objectId) => ({
      object_type: "term",
      object_id: objectId,
      chunk_type: "ontology_term",
      source_kind: "ontology_terms",
      source_refs_json: JSON.stringify([{ table: "ontology_terms", id: objectId }]),
      chunk_text: [row.term_kind, row.label, row.definition, row.aliases_json].filter(Boolean).join("\n")
    }));
  }
  for (const row of database.prepare("SELECT rowid, node_id, node_type, canonical_label, summary, attributes_json FROM ontology_nodes WHERE ontology_id = ?").all(ontologyId)) {
    pushChunk(chunks, skipped, "ontology_nodes", "node_id", row, (objectId) => ({
      object_type: "node",
      object_id: objectId,
      chunk_type: "ontology_node",
      source_kind: "ontology_nodes",
      source_refs_json: JSON.stringify([{ table: "ontology_nodes", id: objectId }]),
      chunk_text: [row.node_type, row.canonical_label, row.summary, row.attributes_json].filter(Boolean).join("\n")
    }));
  }
  for (const row of database.prepare("SELECT rowid, edge_id, relation_type, relation_label, attributes_json FROM ontology_edges WHERE ontology_id = ?").all(ontologyId)) {
    pushChunk(chunks, skipped, "ontology_edges", "edge_id", row, (objectId) => ({
      object_type: "edge",
      object_id: objectId,
      chunk_type: "ontology_edge",
      source_kind: "ontology_edges",
      source_refs_json: JSON.stringify([{ table: "ontology_edges", id: objectId }]),
      chunk_text: [row.relation_type, row.relation_label, row.attributes_json].filter(Boolean).join("\n")
    }));
  }
  for (const row of database.prepare("SELECT rowid, assertion_id, subject_ref_type, subject_ref_id, predicate, object_ref_type, object_ref_id, value_text FROM ontology_assertions WHERE ontology_id = ?").all(ontologyId)) {
    pushChunk(chunks, skipped, "ontology_assertions", "assertion_id", row, (objectId) => ({
      object_type: "assertion",
      object_id: objectId,
      chunk_type: "ontology_assertion",
      source_kind: "ontology_assertions",
      source_refs_json: JSON.stringify([{ table: "ontology_assertions", id: objectId }]),
      chunk_text: [row.subject_ref_type, row.subject_ref_id, row.predicate, row.object_ref_type, row.object_ref_id, row.value_text].filter(Boolean).join(" ")
    }));
  }
  return { chunks: chunks.filter((chunk) => chunk.chunk_text.trim()), skipped };
}

export async function refreshOntologyEmbeddings({ database, ontologyIds, runtimeConfig, embedTextsFn }) {
  const ids = [...new Set((ontologyIds || []).map((value) => String(value || "").trim()).filter(Boolean))];
  if (!ids.length) return { status: "skipped", reason: "No ontology ids affected.", refreshed: [] };
  if (typeof embedTextsFn !== "function") return { status: "unavailable", reason: "Embedding function is not configured.", refreshed: [] };
  const refreshed = [];
  for (const ontologyId of ids) {
    const { chunks, skipped } = ontologyObjects(database, ontologyId);
    if (skipped.length) {
      const message = `Ontology objects missing stable IDs; embedding refresh skipped for ${skipped.length} object(s).`;
      database.prepare("UPDATE ontology_lenses SET embedding_status = 'unavailable', embedding_error = ?, embedding_updated_at = CURRENT_TIMESTAMP WHERE ontology_id = ?").run(message, ontologyId);
      refreshed.push({ ontology_id: ontologyId, chunk_count: chunks.length, status: "unavailable", error: message, skipped });
      continue;
    }
    if (!chunks.length) {
      database.prepare("UPDATE ontology_lenses SET embedding_status = 'clean', embedding_error = NULL, embedding_updated_at = CURRENT_TIMESTAMP WHERE ontology_id = ?").run(ontologyId);
      refreshed.push({ ontology_id: ontologyId, chunk_count: 0, status: "clean" });
      continue;
    }
    try {
      const vectors = await embedTextsFn(runtimeConfig, chunks.map((chunk) => chunk.chunk_text));
      database.exec("BEGIN IMMEDIATE");
      database.prepare("DELETE FROM ontology_embedding_chunks WHERE ontology_id = ?").run(ontologyId);
      const statement = database.prepare(
        "INSERT INTO ontology_embedding_chunks (chunk_id, ontology_id, object_type, object_id, chunk_index, chunk_type, source_kind, source_refs_json, chunk_text, vector, model, dimensions, created_at) "
        + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)"
      );
      chunks.forEach((chunk, index) => {
        const vector = vectors[index] || [];
        statement.run(
          `och_${randomUUID()}`,
          ontologyId,
          chunk.object_type,
          chunk.object_id,
          index,
          chunk.chunk_type,
          chunk.source_kind,
          chunk.source_refs_json,
          chunk.chunk_text,
          vectorToBuffer(vector),
          runtimeConfig?.embedding_model || "unknown",
          vector.length || 0
        );
      });
      database.prepare("UPDATE ontology_lenses SET embedding_status = 'clean', embedding_error = NULL, embedding_updated_at = CURRENT_TIMESTAMP WHERE ontology_id = ?").run(ontologyId);
      database.exec("COMMIT");
      refreshed.push({ ontology_id: ontologyId, chunk_count: chunks.length, status: "clean" });
    } catch (error) {
      try {
        database.exec("ROLLBACK");
      } catch {
        // The embedding refresh transaction may not have started yet.
      }
      const message = error instanceof Error ? error.message : "Ontology embedding refresh failed.";
      database.prepare("UPDATE ontology_lenses SET embedding_status = 'unavailable', embedding_error = ?, embedding_updated_at = CURRENT_TIMESTAMP WHERE ontology_id = ?").run(message, ontologyId);
      refreshed.push({ ontology_id: ontologyId, chunk_count: chunks.length, status: "unavailable", error: message });
    }
  }
  return { status: refreshed.some((item) => item.status === "unavailable") ? "warning" : "ok", refreshed };
}
