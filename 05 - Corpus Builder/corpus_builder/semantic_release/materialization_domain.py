"""Pure domain builders for document materialization records."""
from __future__ import annotations

from typing import Any

from ..models.serialization import now_iso
from .record_domain import (
    build_attribute_record,
    build_entity_record,
    build_fingerprint_audit,
    build_missing_binding_audit,
)
from .types import MaterializationInputs, MaterializedSemantics, SlotCandidate


def build_materialization_result(
    inputs: MaterializationInputs,
    slot_candidates: list[SlotCandidate],
    document_promotions: list[dict[str, Any]],
) -> MaterializedSemantics:
    entities, attributes = _context_records(inputs)
    field_entities, field_attributes, audits = _field_records(inputs)
    row_entities, row_attributes = _row_records(inputs)
    entities.extend(field_entities)
    entities.extend(row_entities)
    attributes.extend(field_attributes)
    attributes.extend(row_attributes)
    relations = _relation_records(inputs.payload)
    projection_id = inputs.projection_meta["projection_id"]
    release_fingerprint = str(inputs.projection.get("projection_fingerprint") or "")
    input_fingerprint = str(inputs.projection_meta.get("projection_fingerprint") or "")
    materialization_state, stale_reason = "current", None
    if input_fingerprint and release_fingerprint and input_fingerprint != release_fingerprint:
        materialization_state, stale_reason = "stale", "projection_fingerprint_mismatch"
        audits.append(build_fingerprint_audit(inputs.document_id, projection_id, input_fingerprint, release_fingerprint))
    return {
        "projection_id": projection_id,
        "projection_fingerprint": release_fingerprint,
        "document_promotions": document_promotions,
        "slot_candidates": slot_candidates,
        "entities": entities,
        "entity_attributes": attributes,
        "entity_relations": relations,
        "processing_state": {
            "document_id": inputs.document_id,
            "schema_version": str(inputs.payload.get("schema_version") or ""),
            "materialization_version": inputs.materialization_version,
            "materialized_snapshot_id": inputs.active_snapshot_id,
            "projection_id": projection_id,
            "projection_fingerprint": release_fingerprint,
            "materialization_state": materialization_state,
            "stale_reason": stale_reason,
            "source_mode": "normalized",
            "last_materialized_at": now_iso(),
        },
        "audits": audits,
    }


def _context_records(inputs: MaterializationInputs) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    attributes: list[dict[str, Any]] = []
    context = inputs.payload.get("context") if isinstance(inputs.payload.get("context"), dict) else {}
    for list_key, entity_type, role_type in (
        ("people", "party", "person"),
        ("organizations", "party", "organization"),
        ("locations", "address", "location"),
    ):
        for index, value in enumerate(context.get(list_key, []) or []):
            entity_key = f"context:{list_key}:{index}"
            entities.append(build_entity_record(entity_key, entity_type, role_type, value, f"context.{list_key}[{index}]", inputs))
            attributes.append(build_attribute_record(entity_key, "name", value, f"context.{list_key}[{index}]"))
    return entities, attributes


def _field_records(inputs: MaterializationInputs) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    attributes: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    content = inputs.payload.get("content") if isinstance(inputs.payload.get("content"), dict) else {}
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    field_bindings = {
        str(item.get("code") or "").strip(): item
        for item in inputs.projection.get("field_codes", [])
        if isinstance(item, dict)
    }
    for field_code, value in fields.items():
        if str(field_code).startswith("_"):
            continue
        binding = (field_bindings.get(str(field_code)) or {}).get("semantic_binding")
        if not isinstance(binding, dict):
            audits.append(build_missing_binding_audit(inputs.document_id, inputs.projection_meta["projection_id"], str(field_code)))
            continue
        entity_key = f"field:{field_code}"
        entities.append(
            build_entity_record(
                entity_key,
                str(binding.get("entity_type") or "document_fact"),
                str(binding.get("role_type") or "") or None,
                value,
                f"content.fields.{field_code}",
                inputs,
            )
        )
        attributes.append(
            build_attribute_record(
                entity_key,
                str(binding.get("attribute_code") or field_code),
                value,
                f"content.fields.{field_code}",
            )
        )
    return entities, attributes, audits


def _row_records(inputs: MaterializationInputs) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    attributes: list[dict[str, Any]] = []
    content = inputs.payload.get("content") if isinstance(inputs.payload.get("content"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    row_bindings = {
        str(item.get("code") or "").strip(): item
        for item in inputs.projection.get("row_types", [])
        if isinstance(item, dict)
    }
    cell_bindings = {
        str(item.get("code") or "").strip(): item
        for item in inputs.projection.get("cell_codes", [])
        if isinstance(item, dict)
    }
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        row_type = str(row.get("_row_type") or "other").strip()
        row_binding = (row_bindings.get(row_type) or {}).get("semantic_binding")
        if not isinstance(row_binding, dict) or not bool(row_binding.get("materialize_each_row")):
            continue
        entity_key = f"row:{row_index}"
        entities.append(
            build_entity_record(
                entity_key,
                str(row_binding.get("entity_type") or "event"),
                str(row_binding.get("role_type") or row_type),
                row.get("description") or row.get("label") or row_type,
                f"content.rows[{row_index}]",
                inputs,
                row_index=row_index,
            )
        )
        for cell_key, value in row.items():
            if str(cell_key).startswith("_"):
                continue
            cell_binding = (cell_bindings.get(str(cell_key)) or {}).get("semantic_binding")
            attr_code = str(cell_binding.get("attribute_code") if isinstance(cell_binding, dict) else cell_key)
            attributes.append(build_attribute_record(entity_key, attr_code, value, f"content.rows[{row_index}].{cell_key}"))
    return entities, attributes


def _relation_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for index, relation in enumerate(payload.get("relations", []) or []):
        if not isinstance(relation, dict):
            continue
        relations.append(
            {
                "relation_type": str(relation.get("type") or "entity_reference"),
                "target_hint": str(relation.get("target_hint") or relation.get("file_name") or ""),
                "target_document_id": relation.get("target_document_id"),
                "description": relation.get("description"),
                "source_path": f"relations[{index}]",
                "relation_origin": "materialized",
                "status": "materialized",
                "created_by": "semantic_release",
            }
        )
    return relations
