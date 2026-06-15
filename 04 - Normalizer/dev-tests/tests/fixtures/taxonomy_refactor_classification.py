from __future__ import annotations

from tests.fixtures.taxonomy_refactor_paths import CONTRACT_ARTIFACT_KINDS

TEXT_FIELD_NAMES = frozenset(
    {
        "avoid_when",
        "company",
        "description",
        "document_title",
        "free_text",
        "issuer",
        "label",
        "matched_signals",
        "member_name",
        "organization",
        "organizations",
        "people",
        "property_address",
        "reason",
        "recipient_name",
        "review_reason",
        "tags",
        "text",
        "text_markers",
        "warnings",
        "when_to_use",
    }
)
TEXT_PATH_SNIPPETS = (
    "$.compatibility.notes",
    "$.ocr_reference.block_refs.",
    "$.ocr_reference.sections[].text",
    "$.projection.selection.reason",
    "$.context.projection_hint.reason",
    "$.release_analysis.issues",
    "$.release_analysis.warnings",
    "$.routing.surface_signals.domain_markers.",
    "$.routing.surface_signals.text_markers",
)
COMPILED_METADATA_KEYS = frozenset(
    {
        "active_release_fingerprint",
        "active_release_id",
        "active_release_version",
        "catalog_version",
        "created_at",
        "fingerprint",
        "generated_at",
        "materialization_version",
        "pending_release_change",
        "processed_at",
        "projection_count",
        "published_release_fingerprint",
        "published_release_id",
        "published_release_version",
        "release_fingerprint",
        "release_version",
        "schema_version",
    }
)
COMPILED_RUNTIME_KEYS = frozenset({"embedded_documents", "missing_release_documents", "stale_documents", "total_documents"})


def classify_path(artifact_kind: str, json_path: str) -> str:
    if artifact_kind == "master_taxonomy" and json_path.startswith("$.projection_templates"):
        return "compiled_only"
    if artifact_kind == "projection" and json_path in {"$.master_taxonomy_id", "$.master_taxonomy_version", "$.projection_fingerprint"}:
        return "compiled_only"
    if artifact_kind == "release_recipe":
        return "text" if is_text_path(json_path) else "core"
    if artifact_kind in {"semantic_release", "semantic_release_v1"} and _is_semantic_release_compiled_path(json_path):
        return "compiled_only"
    if artifact_kind in {"runtime_semantic_assets", "runtime_semantic_assets_v1"} and _is_runtime_assets_compiled_path(json_path):
        return "compiled_only"
    if artifact_kind == "projection_catalog_v1" and _is_projection_catalog_compiled_path(json_path):
        return "compiled_only"
    if artifact_kind in {"semantic_status_v1", "active_semantic_release_v1"} and _is_runtime_state_compiled_path(json_path):
        return "compiled_only"
    if artifact_kind == "request_envelope_01_02" and json_path.startswith("$.projection_catalog") and _has_compiled_metadata_key(json_path):
        return "compiled_only"
    if artifact_kind in {"structured_output_02_04", "normalized_output_04_downstream"}:
        if json_path in {"$.schema_version", "$.processing.processed_at"}:
            return "compiled_only"
        if json_path.startswith("$.projection.selection.") and _has_compiled_metadata_key(json_path):
            return "compiled_only"
    if json_path == "$.schema_version":
        return "compiled_only"
    return "text" if is_text_path(json_path) else "core"


def inventory_location_key_for(artifact_kind: str) -> str:
    return "origin_bucket" if artifact_kind in CONTRACT_ARTIFACT_KINDS else "target_source"


def inventory_location_value_for(artifact_kind: str, classification: str, *, projection_id: str | None) -> str:
    if artifact_kind in CONTRACT_ARTIFACT_KINDS:
        return origin_bucket_for(artifact_kind)
    return target_source_for(artifact_kind, classification, projection_id)


def target_source_for(artifact_kind: str, classification: str, projection_id: str | None) -> str:
    if classification == "compiled_only":
        return "compiled_only"
    if artifact_kind == "master_taxonomy":
        return "master.text.en.yaml" if classification == "text" else "master.core.yaml"
    if artifact_kind == "projection":
        if not projection_id:
            raise ValueError("projection_id ist fuer Projection-Inventur erforderlich.")
        return f"projections/{projection_id}.{'text.en.yaml' if classification == 'text' else 'core.yaml'}"
    if artifact_kind == "release_recipe":
        return "release.yaml"
    if artifact_kind in {"semantic_release", "runtime_semantic_assets"}:
        return "compiled_only"
    raise ValueError(f"Unbekannter artifact_kind: {artifact_kind}")


def origin_bucket_for(artifact_kind: str) -> str:
    buckets = {
        "request_envelope_01_02": "upstream_request",
        "structured_output_02_04": "interpreter_output",
        "normalized_output_04_downstream": "downstream_payload",
        "projection_catalog_v1": "compiled_projection",
        "semantic_release_v1": "compiled_release",
        "runtime_semantic_assets_v1": "runtime_bundle",
        "semantic_status_v1": "corpus_runtime_state",
        "active_semantic_release_v1": "corpus_runtime_state",
    }
    try:
        return buckets[artifact_kind]
    except KeyError as exc:
        raise ValueError(f"Unbekannter Contract-Artifact-Typ: {artifact_kind}") from exc


def is_text_path(json_path: str) -> bool:
    if any(snippet in json_path for snippet in TEXT_PATH_SNIPPETS):
        return True
    if json_path.endswith(".aliases") or json_path.endswith(".aliases[]"):
        return True
    leaf_name = _leaf_name(json_path)
    return leaf_name in TEXT_FIELD_NAMES or (json_path.endswith("[]") and leaf_name in TEXT_FIELD_NAMES)


def _is_semantic_release_compiled_path(json_path: str) -> bool:
    if json_path.startswith("$.master_taxonomy.projection_templates"):
        return True
    if json_path in {"$.created_at", "$.fingerprint", "$.materialization_version", "$.release_version"}:
        return True
    return json_path.endswith(".projection_fingerprint") or json_path.endswith(".projection_version")


def _is_runtime_assets_compiled_path(json_path: str) -> bool:
    return _has_compiled_metadata_key(json_path) or json_path.endswith(".projection_fingerprint") or json_path.endswith(".policy_bundle_version")


def _is_projection_catalog_compiled_path(json_path: str) -> bool:
    return _has_compiled_metadata_key(json_path)


def _is_runtime_state_compiled_path(json_path: str) -> bool:
    if json_path.startswith("$.release.") and _is_semantic_release_compiled_path("$" + json_path.removeprefix("$.release")):
        return True
    if json_path.startswith("$.status.") and (
        _has_compiled_metadata_key("$" + json_path.removeprefix("$.status")) or _leaf_name(json_path) in COMPILED_RUNTIME_KEYS
    ):
        return True
    return _has_compiled_metadata_key(json_path) or _leaf_name(json_path) in COMPILED_RUNTIME_KEYS


def _has_compiled_metadata_key(json_path: str) -> bool:
    return _leaf_name(json_path) in COMPILED_METADATA_KEYS


def _leaf_name(json_path: str) -> str:
    return json_path.replace("[]", "").split(".")[-1]
