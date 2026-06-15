from __future__ import annotations

from pathlib import Path
from typing import Any

from ..semantic_release.kernel_candidate import stable_hash
from .kernel_component_materialization import artifact_ref, write_component
from .kernel_release_domain_helpers import (
    mapping as _mapping,
    owner_ok as _owner_ok,
    projection_component_identity as _projection_component_identity,
)
from .kernel_update_state_mapping import extract_update_state, projection_identity, taxonomy_identity


def materialize_custom_taxonomy_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    update_state = extract_update_state(payload, "update_state_payload", "update_state")
    target_identity = _mapping(payload, "target_identity")
    identity = taxonomy_identity(update_state)
    stage_id = f"tax_{stable_hash(repr(sorted(identity.items())))[:12]}"
    base = Path(str(payload["semantic_release_folder"])) / "staged" / "taxonomy" / stage_id
    written = write_component(base / "taxonomy.json", {"identity": identity, "update_state": update_state})
    output = {
        "taxonomy_artifact_ref": artifact_ref(written, root=payload["semantic_release_folder"]),
        "artifact_ref": artifact_ref(written, root=payload["semantic_release_folder"]),
        "taxonomy_id": identity["taxonomy_id"],
        "taxonomy_fingerprint": identity["taxonomy_fingerprint"],
        "component_identity": identity,
        "stage_id": stage_id,
        "written_paths": [written],
        "validation_status": "validated",
    }
    return _owner_ok("materialize_custom_taxonomy_artifact", "semantic_release_domain_service", target_identity, output)


def materialize_custom_projection_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    update_state = extract_update_state(payload, "update_state_payload", "update_state")
    target_identity = _mapping(payload, "target_identity")
    taxonomy_ref = _mapping(payload, "taxonomy_ref")
    identity = projection_identity(update_state, taxonomy_ref=taxonomy_ref)
    stage_id = f"proj_{stable_hash(repr(sorted(identity.items())))[:12]}"
    base = Path(str(payload["semantic_release_folder"])) / "staged" / "projections" / stage_id
    written = write_component(
        base / "projections.json",
        {"identity": identity, "update_state": update_state, "taxonomy_ref": taxonomy_ref},
    )
    projection_refs = [
        {
            "projection_id": projection_id,
            "projection_fingerprint": identity["projection_fingerprints"][projection_id],
            "included_taxonomy_codes": list(identity["included_taxonomy_codes"]),
        }
        for projection_id in identity["projection_ids"]
    ]
    projection_set_fingerprint = stable_hash(repr(projection_refs))
    output = {
        "projection_artifact_refs": [artifact_ref(written, root=payload["semantic_release_folder"])],
        "artifact_ref": artifact_ref(written, root=payload["semantic_release_folder"]),
        "projection_ids": list(identity["projection_ids"]),
        "projection_fingerprints": dict(identity["projection_fingerprints"]),
        "projection_refs": projection_refs,
        "projection_set_fingerprint": projection_set_fingerprint,
        "component_identity": _projection_component_identity(projection_refs, projection_set_fingerprint),
        "stage_id": stage_id,
        "written_paths": [written],
        "validation_summary": {"projection_count": len(projection_refs)},
    }
    return _owner_ok("materialize_custom_projection_artifact", "semantic_release_domain_service", target_identity, output)
