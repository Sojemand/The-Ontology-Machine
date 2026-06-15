import { MAX_TEXT_LENGTH } from "./types.js";
import { cleanArtifactFileName, clipText, corpusRef, sanitizeRow } from "./output_policy.js";
import { getAvailableColumns, getOptionalRow, listOptionalRows, listStringsFromTable } from "./corpus_tables.js";
import { normalizeDocumentViewName, resolveDocumentViewLimits, sourceDocumentContext, structuralUnits } from "./document_view_support.js";
import { listDocumentPromotions, promotionActor, promotionDate, promotionSummary, promotionTitle } from "./promotion_surface.js";

export function createDocumentRepository({ database, buildSource, imageRepository }) {
  function getDocumentView(docId, runtimePolicy = null, viewName = "full") {
    const normalizedView = normalizeDocumentViewName(viewName);
    const limits = resolveDocumentViewLimits(runtimePolicy, normalizedView);
    const maxTextLength = runtimePolicy?.max_text_length || MAX_TEXT_LENGTH;
    const document = database.prepare("SELECT * FROM documents WHERE id = ?").get(docId);
    if (!document) return { found: false, doc_id: docId };
    const source = buildSource(docId);
    const pages = imageRepository.buildPages(document);
    const viewerAvailable = pages.some((page) => page.available);
    const payloadColumns = getAvailableColumns(database, "document_payloads", ["free_text", "normalized_json", "structured_json", "projection_json"]);
    const payload = payloadColumns.length
      ? getOptionalRow(database, "document_payloads", `SELECT ${payloadColumns.join(", ")} FROM document_payloads WHERE document_id = ?`, [docId])
      : null;
    const fieldColumns = getAvailableColumns(database, "extracted_fields", ["key", "value", "value_type", "numeric_value", "confidence", "source", "normalized_value", "compact_value"]);
    const slotCandidateColumns = getAvailableColumns(database, "slot_candidates", ["slot", "display_value", "strategy", "confidence", "is_projection_backed", "origin_path"]);
    const documentPromotions = listDocumentPromotions(database, docId, limits.fields).map(sanitizeRow);
    const resolvedTitle = promotionTitle(documentPromotions, document.file_name);
    const resolvedActor = promotionActor(documentPromotions);
    const resolvedDate = promotionDate(documentPromotions);
    const evidence = listOptionalRows(
      database,
      "evidence_atoms",
      "SELECT atom_type, json_path, page, source_ref, text_value, context_label, context_window FROM evidence_atoms WHERE document_id = ? ORDER BY atom_id LIMIT ?",
      [docId, limits.evidence]
    ).map(sanitizeRow);
    const sourceContext = sourceDocumentContext(database, docId);
    const sourceDocumentId = sourceContext.page?.source_document_id || sourceContext.source_document?.source_document_id || "";
    const unitLimit = Math.max(1, Math.min(12, limits.evidence || 12));
    const units = structuralUnits(database, docId, sourceDocumentId, unitLimit);
    const basePayload = {
      found: true,
      document_view: normalizedView,
      source,
      document: sanitizeRow({
        id: document.id,
        title: resolvedTitle,
        file_name: cleanArtifactFileName(document.file_name, document),
        file_path: corpusRef(document),
        type: document.document_type,
        category: document.category,
        subcategory: document.subcategory,
        date: resolvedDate,
        actor: resolvedActor,
        description: promotionSummary(documentPromotions) || null,
        page_count: pages.length || 1,
        viewer_available: viewerAvailable,
        viewer_reason: viewerAvailable ? null : "missing_document_images"
      }),
      pages,
      source_document_context: sourceContext,
      layer_info: {
        active_sql_layer: "normalized_first",
        preferred_payload_layer: payload?.normalized_json ? "normalized" : payload?.structured_json ? "structured" : null,
        normalized_payload_available: Boolean(payload?.normalized_json),
        structured_payload_available: Boolean(payload?.structured_json),
        free_text_source: payload?.free_text ? "document_payloads.free_text" : document.content_free_text ? "documents.content_free_text" : null,
        promotion_surface_available: documentPromotions.length > 0,
        active_fact_surface: documentPromotions.length > 0 ? "document_promotions" : null
      },
      limits: {
        fields: limits.fields,
        rows: limits.rows,
        evidence_atoms: limits.evidence,
        text_chars: limits.text
      }
    };
    const people = listStringsFromTable(database, "people", "name", docId);
    const organizations = listStringsFromTable(database, "organizations", "name", docId);
    const tags = listStringsFromTable(database, "tags", "tag", docId);
    const fields = fieldColumns.includes("key") && fieldColumns.includes("value")
      ? listOptionalRows(database, "extracted_fields", `SELECT ${fieldColumns.join(", ")} FROM extracted_fields WHERE document_id = ? ORDER BY key, value LIMIT ?`, [docId, limits.fields]).map(sanitizeRow)
      : [];
    const rows = listOptionalRows(database, "extracted_rows", "SELECT row_index, row_json FROM extracted_rows WHERE document_id = ? ORDER BY row_index LIMIT ?", [docId, limits.rows])
      .map((row) => ({ row_index: row.row_index, row_json: clipText(row.row_json, 1_500) }));
    const slotCandidates = slotCandidateColumns.includes("slot") && slotCandidateColumns.includes("display_value")
      ? listOptionalRows(database, "slot_candidates", `SELECT ${slotCandidateColumns.join(", ")} FROM slot_candidates WHERE document_id = ? ORDER BY COALESCE(is_projection_backed, 0) DESC, COALESCE(confidence, 0) DESC, rowid ASC LIMIT ?`, [docId, limits.fields]).map(sanitizeRow)
      : [];
    const sourceRefs = Array.from(new Set(evidence.map((item) => item.source_ref).filter(Boolean)));
    const excerpts = {
      free_text_excerpt: clipText(payload?.free_text || document.content_free_text || "", normalizedView === "full" ? maxTextLength : limits.text),
      normalized_excerpt: clipText(payload?.normalized_json || "", limits.payload.normalized),
      structured_excerpt: clipText(payload?.structured_json || "", limits.payload.structured),
      projection_excerpt: clipText(payload?.projection_json || "", limits.payload.projection)
    };

    if (normalizedView === "summary") {
      return {
        ...basePayload,
        people,
        organizations,
        tags,
        document_promotions: documentPromotions,
        structural_units: units,
        ...excerpts
      };
    }
    if (normalizedView === "rows") {
      return {
        ...basePayload,
        document_promotions: documentPromotions,
        rows,
        slot_candidates: slotCandidates,
        evidence_atoms: evidence,
        source_refs: sourceRefs,
        free_text_excerpt: excerpts.free_text_excerpt,
        structured_excerpt: excerpts.structured_excerpt
      };
    }
    if (normalizedView === "ontology_evidence" || normalizedView === "provenance") {
      return {
        ...basePayload,
        people,
        organizations,
        tags,
        document_promotions: documentPromotions,
        fields,
        rows,
        slot_candidates: slotCandidates,
        structural_units: units,
        source_refs: sourceRefs,
        evidence_atoms: evidence,
        ...excerpts
      };
    }
    return {
      ...basePayload,
      people,
      organizations,
      tags,
      document_promotions: documentPromotions,
      fields,
      rows,
      slot_candidates: slotCandidates,
      source_refs: sourceRefs,
      evidence_atoms: evidence,
      ...excerpts
    };
  }

  return {
    getDocument(docId, runtimePolicy = null) {
      return getDocumentView(docId, runtimePolicy, "full");
    },
    getDocumentSummary(docId, runtimePolicy = null) {
      return getDocumentView(docId, runtimePolicy, "summary");
    },
    getDocumentOntologyEvidence(docId, runtimePolicy = null) {
      return getDocumentView(docId, runtimePolicy, "ontology_evidence");
    },
    getDocumentRows(docId, runtimePolicy = null) {
      return getDocumentView(docId, runtimePolicy, "rows");
    },
    getDocumentProvenance(docId, runtimePolicy = null) {
      return getDocumentView(docId, runtimePolicy, "provenance");
    },
    getDocumentFull(docId, runtimePolicy = null) {
      return getDocumentView(docId, runtimePolicy, "full");
    }
  };
}
