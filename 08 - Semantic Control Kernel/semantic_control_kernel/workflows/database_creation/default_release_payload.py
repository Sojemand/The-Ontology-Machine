from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash


def default_release_payload_from_adapter_output(output: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(output)
    if isinstance(normalized.get("release_ref"), Mapping):
        release_ref = dict(normalized["release_ref"])
        if normalized.get("output_path"):
            release_ref.setdefault("source_adapter_receipt_ref", {})["output_path"] = str(normalized["output_path"])
        return release_ref
    output_path = str(normalized.get("output_path") or "").strip()
    if output_path:
        try:
            release_payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            release_payload = {}
        if isinstance(release_payload, Mapping):
            release_ref = semantic_release_to_default_ref(release_payload)
            release_ref["output_path"] = output_path
            return release_ref
    if "fingerprint" in normalized and "release_fingerprint" not in normalized:
        normalized["release_fingerprint"] = normalized["fingerprint"]
    return normalized


def semantic_release_to_default_ref(release: Mapping[str, Any]) -> dict[str, Any]:
    release_id = str(release.get("release_id") or "")
    release_version = str(release.get("release_version") or "")
    release_fingerprint = str(release.get("release_fingerprint") or release.get("fingerprint") or "")
    master = release.get("master_taxonomy") if isinstance(release.get("master_taxonomy"), Mapping) else {}
    taxonomy_id = str(
        release.get("master_taxonomy_release_id")
        or release.get("master_taxonomy_id")
        or master.get("taxonomy_id")
        or "default.taxonomy"
    )
    taxonomy_fingerprint = str(
        release.get("master_taxonomy_release_id")
        or master.get("taxonomy_fingerprint")
        or stable_hash(json.dumps(master, sort_keys=True, default=str))
    )
    return {
        "release_id": release_id,
        "release_version": release_version,
        "release_fingerprint": release_fingerprint,
        "taxonomy_ref": {
            "taxonomy_id": taxonomy_id,
            "taxonomy_fingerprint": taxonomy_fingerprint,
            "runtime_locale": str(release.get("runtime_locale") or ""),
        },
        "projection_refs": _projection_refs(release),
    }


def _projection_refs(release: Mapping[str, Any]) -> list[dict[str, str]]:
    projection_refs = []
    projections = release.get("projections")
    if isinstance(projections, list):
        for index, projection in enumerate(projections, start=1):
            if not isinstance(projection, Mapping):
                continue
            projection_id = str(projection.get("projection_id") or projection.get("id") or f"default.projection.{index}")
            projection_fingerprint = str(
                projection.get("projection_fingerprint")
                or projection.get("fingerprint")
                or stable_hash(json.dumps(projection, sort_keys=True, default=str))
            )
            projection_refs.append({"projection_id": projection_id, "projection_fingerprint": projection_fingerprint})
    if not projection_refs:
        for projection_id in release.get("projection_ids", ()):
            if projection_id:
                projection_refs.append({"projection_id": str(projection_id), "projection_fingerprint": stable_hash(str(projection_id))})
    return projection_refs
