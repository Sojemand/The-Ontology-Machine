"""Observed semantic graph builders for interpreter-native segments."""

from __future__ import annotations

import json
from typing import Any

from ..models.serialization import now_iso
from .policy import is_non_empty, normalize_search_text
from .types import JsonDict


def split_relations(relations: list[JsonDict]) -> tuple[list[JsonDict], list[JsonDict]]:
    graph_relations: list[JsonDict] = []
    document_relations: list[JsonDict] = []
    for relation in relations:
        if _has_segment_link(relation):
            graph_relations.append(relation)
        else:
            document_relations.append(relation)
    return document_relations, graph_relations


def build_observed_semantics(segments: list[JsonDict], relations: list[JsonDict]) -> JsonDict:
    entities: list[JsonDict] = []
    attributes: list[JsonDict] = []
    entity_relations: list[JsonDict] = []
    segment_keys: dict[str, str] = {}
    for index, segment in enumerate(segments):
        segment_id = str(segment.get("segment_id") or "").strip()
        if not segment_id:
            continue
        entity_key = f"segment:{segment_id}"
        segment_keys[segment_id] = entity_key
        source_path = f"content.segments[{index}]"
        text = str(segment.get("text") or "")
        display_value = str(segment.get("label") or text or segment.get("unit_kind") or "").strip() or None
        entities.append(
            {
                "entity_key": entity_key,
                "entity_type": "segment",
                "role_type": str(segment.get("unit_kind") or "").strip() or "other",
                "display_value": display_value,
                "normalized_value": normalize_search_text(display_value or text),
                "source_path": source_path,
                "row_index": None,
                "page": segment.get("page"),
                "sequence": segment.get("sequence"),
                "projection_id": None,
                "materialization_version": None,
                "state": "observed",
            }
        )
        _append_attribute(attributes, entity_key, "text", segment.get("text"), f"{source_path}.text")
        _append_attribute(attributes, entity_key, "label", segment.get("label"), f"{source_path}.label")
        _append_attribute(attributes, entity_key, "function", segment.get("function"), f"{source_path}.function")
        _append_attribute(attributes, entity_key, "section", segment.get("section"), f"{source_path}.section")
        _append_attribute(attributes, entity_key, "confidence", segment.get("confidence"), f"{source_path}.confidence")
        if isinstance(segment.get("attributes"), dict):
            for key, value in segment["attributes"].items():
                if not str(key).startswith("_"):
                    _append_attribute(attributes, entity_key, str(key), value, f"{source_path}.attributes.{key}")
        if isinstance(segment.get("_source_refs"), dict):
            _append_attribute(attributes, entity_key, "source_refs", segment.get("_source_refs"), f"{source_path}._source_refs")
    for index, relation in enumerate(relations):
        source_key = segment_keys.get(str(relation.get("source_id") or "").strip())
        target_key = segment_keys.get(str(relation.get("target_id") or "").strip())
        if source_key is None or target_key is None:
            continue
        entity_relations.append(
            {
                "relation_type": str(relation.get("type") or "related_to"),
                "source_entity_key": source_key,
                "target_entity_key": target_key,
                "target_document_id": relation.get("target_document_id"),
                "target_hint": relation.get("target_hint"),
                "description": relation.get("description"),
                "source_path": f"relations[{index}]",
                "relation_origin": "observed",
                "confidence": relation.get("confidence"),
                "evidence_refs": relation.get("evidence_refs") or [f"relations[{index}]"],
                "inference_policy_version": relation.get("inference_policy_version"),
                "status": relation.get("status") or "observed",
                "created_by": relation.get("created_by") or "corpus_builder",
                "created_at": relation.get("created_at") or now_iso(),
            }
        )
    return {"entities": entities, "entity_attributes": attributes, "entity_relations": entity_relations}


def _append_attribute(target: list[JsonDict], entity_key: str, code: str, value: Any, source_path: str) -> None:
    if not is_non_empty(value):
        return
    target.append(
        {
            "entity_key": entity_key,
            "attribute_code": code,
            "display_value": None if isinstance(value, (dict, list)) else str(value),
            "normalized_value": normalize_search_text(value) if not isinstance(value, (dict, list)) else None,
            "numeric_value": float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
            "date_value": value if isinstance(value, str) and len(value) == 10 and value[4:5] == "-" and value[7:8] == "-" else None,
            "value_json": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else None,
            "source_path": source_path,
        }
    )


def _has_segment_link(relation: JsonDict) -> bool:
    return is_non_empty(relation.get("source_id")) and is_non_empty(relation.get("target_id"))


__all__ = ["build_observed_semantics", "split_relations"]
