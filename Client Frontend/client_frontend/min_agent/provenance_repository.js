import { MAX_EVIDENCE_COUNT, MAX_FIELD_COUNT } from "./types.js";
import { sanitizeRow } from "./output_policy.js";
import { getAvailableColumns, listOptionalRows, tableExists } from "./corpus_tables.js";
import { promotionColumns } from "./promotion_surface.js";

function normalizeTargetKind(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "field" || normalized === "slot" || normalized === "promotion" ? normalized : "auto";
}

export function createProvenanceRepository({ database, buildSource }) {
  return {
    getProvenance(docId, target, targetKind = "auto", runtimePolicy = null) {
      const maxEvidenceCount = runtimePolicy?.max_evidence_count || MAX_EVIDENCE_COUNT;
      const maxFieldCount = runtimePolicy?.max_field_count || MAX_FIELD_COUNT;
      const normalizedTarget = String(target || "").trim();
      if (!normalizedTarget) return { found: false, doc_id: String(docId || ""), target: normalizedTarget, error: "get_provenance braucht einen target-Wert." };
      if (!database.prepare("SELECT id FROM documents WHERE id = ?").get(docId)) return { found: false, doc_id: String(docId || ""), target: normalizedTarget };
      const source = buildSource(docId);
      const resolvedKind = normalizeTargetKind(targetKind);
      const fieldColumns = getAvailableColumns(database, "extracted_fields", ["key", "value", "value_type", "numeric_value", "confidence", "source", "normalized_value", "compact_value"]);
      const slotCandidateColumns = getAvailableColumns(database, "slot_candidates", ["candidate_id", "slot", "display_value", "strategy", "confidence", "is_projection_backed", "origin_path", "origin_kind", "source_refs_json"]);
      const promotionTableColumns = promotionColumns(database);
      const evidenceColumns = getAvailableColumns(database, "evidence_atoms", ["atom_id", "atom_type", "json_path", "page", "source_ref", "text_value", "context_label", "context_window"]);
      const promotionCurrentWhere = promotionTableColumns.includes("is_current") ? "AND COALESCE(is_current, 1) = 1" : "";
      const promotionOrderBy = [
        promotionTableColumns.includes("ordinal") ? "COALESCE(ordinal, 0)" : "",
        promotionTableColumns.includes("promotion_id") ? "promotion_id" : ""
      ].filter(Boolean).join(", ") || "slot";
      const fields = resolvedKind !== "slot" && resolvedKind !== "promotion" && fieldColumns.includes("key") && fieldColumns.includes("value")
        ? listOptionalRows(database, "extracted_fields", `SELECT ${fieldColumns.join(", ")} FROM extracted_fields WHERE document_id = ? AND lower(key) = lower(?) ORDER BY key, value LIMIT ?`, [docId, normalizedTarget, maxFieldCount]).map(sanitizeRow)
        : [];
      const promotions = resolvedKind !== "field" && promotionTableColumns.includes("slot") && promotionTableColumns.includes("display_value")
        ? listOptionalRows(database, "document_promotions", `SELECT ${promotionTableColumns.join(", ")} FROM document_promotions WHERE document_id = ? AND lower(slot) = lower(?) ${promotionCurrentWhere} ORDER BY ${promotionOrderBy} LIMIT ?`, [docId, normalizedTarget, maxFieldCount]).map(sanitizeRow)
        : [];
      const slotCandidates = resolvedKind !== "field" && slotCandidateColumns.includes("slot") && slotCandidateColumns.includes("display_value")
        ? listOptionalRows(database, "slot_candidates", `SELECT ${slotCandidateColumns.join(", ")} FROM slot_candidates WHERE document_id = ? AND lower(slot) = lower(?) ORDER BY COALESCE(is_projection_backed, 0) DESC, COALESCE(confidence, 0) DESC, candidate_id ASC LIMIT ?`, [docId, normalizedTarget, maxFieldCount]).map(sanitizeRow)
        : [];
      let linkedEvidenceAtoms = [];
      if (tableExists(database, "candidate_evidence") && evidenceColumns.includes("atom_id") && slotCandidateColumns.includes("candidate_id")) {
        if (promotions.length && promotionTableColumns.includes("candidate_id")) {
          linkedEvidenceAtoms = listOptionalRows(database, "candidate_evidence", `SELECT DISTINCT ce.candidate_id AS candidate_id, ${evidenceColumns.map((column) => `ea.${column} AS ${column}`).join(", ")} FROM candidate_evidence ce JOIN evidence_atoms ea ON ea.atom_id = ce.atom_id JOIN document_promotions dp ON dp.candidate_id = ce.candidate_id WHERE dp.document_id = ? AND lower(dp.slot) = lower(?) ORDER BY ea.atom_id ASC LIMIT ?`, [docId, normalizedTarget, maxEvidenceCount]).map(sanitizeRow);
        } else if (slotCandidates.length) {
          linkedEvidenceAtoms = listOptionalRows(database, "candidate_evidence", `SELECT ce.candidate_id AS candidate_id, ${evidenceColumns.map((column) => `ea.${column} AS ${column}`).join(", ")} FROM candidate_evidence ce JOIN evidence_atoms ea ON ea.atom_id = ce.atom_id JOIN slot_candidates sc ON sc.candidate_id = ce.candidate_id WHERE sc.document_id = ? AND lower(sc.slot) = lower(?) ORDER BY COALESCE(sc.is_projection_backed, 0) DESC, COALESCE(sc.confidence, 0) DESC, ea.atom_id ASC LIMIT ?`, [docId, normalizedTarget, maxEvidenceCount]).map(sanitizeRow);
        }
      }
      const directEvidenceAtoms = evidenceColumns.length
        ? listOptionalRows(database, "evidence_atoms", `SELECT ${evidenceColumns.join(", ")} FROM evidence_atoms WHERE document_id = ? AND (lower(COALESCE(context_label, '')) = lower(?) OR lower(COALESCE(json_path, '')) LIKE lower(?)) ORDER BY atom_id ASC LIMIT ?`, [docId, normalizedTarget, `%${normalizedTarget}%`, maxEvidenceCount]).map(sanitizeRow)
        : [];
      const bestField = fields[0] || null;
      const bestPromotion = promotions[0] || null;
      const bestCandidate = slotCandidates[0] || null;
      return {
        found: true,
        doc_id: String(docId),
        target: normalizedTarget,
        target_kind: resolvedKind,
        source,
        layer_info: {
          active_sql_layer: "normalized_first",
          active_value_layer: bestPromotion ? "document_promotions" : bestField ? "normalized_first_sql" : bestCandidate ? "structured_provenance" : null,
          active_value_source: bestPromotion?.source_path || bestField?.source || bestCandidate?.strategy || null,
          matched_field_count: fields.length,
          matched_promotion_count: promotions.length,
          matched_slot_candidate_count: slotCandidates.length,
          linked_evidence_count: linkedEvidenceAtoms.length,
          direct_evidence_count: directEvidenceAtoms.length
        },
        active_value: bestPromotion?.display_value ?? bestField?.value ?? bestCandidate?.display_value ?? null,
        document_promotions: promotions,
        fields,
        slot_candidates: slotCandidates,
        linked_evidence_atoms: linkedEvidenceAtoms,
        direct_evidence_atoms: directEvidenceAtoms
      };
    }
  };
}
