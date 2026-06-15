from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def artifact_ref_for_path(selection: Mapping[str, Any], path: str | Path) -> dict[str, str]:
    root = _artifact_root(selection)
    target = Path(path).resolve(strict=False)
    return {"artifact_path": target.relative_to(root).as_posix()}


def compact_artifact_copy_report(output: Mapping[str, Any]) -> dict[str, Any]:
    report = output.get("artifact_copy_report")
    if not isinstance(report, Mapping):
        return {}
    return {"copied_artifact_count": int(report.get("copied_artifact_count") or 0)}


def compact_id_map(id_map: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(id_map.get("schema_version", "")),
        "merge_run_id": str(id_map.get("merge_run_id", "")),
        "record_count": int(id_map.get("record_count") or 0),
        "map_fingerprint": str(id_map.get("map_fingerprint", "")),
    }


def id_map_mappings_from_owner(selection: Mapping[str, Any], output: Mapping[str, Any]) -> list[dict[str, Any]]:
    inline = output.get("id_map_mappings")
    if isinstance(inline, list) and inline:
        return [dict(item) for item in inline if isinstance(item, Mapping)]
    ref = output.get("merge_id_map_ref")
    if isinstance(ref, Mapping) and ref.get("artifact_path"):
        payload = _load_json_object(_artifact_path_from_ref(selection, ref))
        mappings = payload.get("mappings")
        if isinstance(mappings, list):
            return [dict(item) for item in mappings if isinstance(item, Mapping)]
    return []


def _artifact_path_from_ref(selection: Mapping[str, Any], ref: Mapping[str, Any]) -> Path:
    artifact_path = str(ref.get("artifact_path") or "").strip()
    if not artifact_path:
        raise ValueError("owner artifact ref is missing artifact_path.")
    root = _artifact_root(selection)
    target = (root / artifact_path).resolve(strict=False)
    target.relative_to(root)
    return target


def _artifact_root(selection: Mapping[str, Any]) -> Path:
    root_text = str(selection.get("target_artifact_root") or "").strip()
    if not root_text:
        raise ValueError("target_artifact_root is required for owner artifact refs.")
    return Path(root_text).resolve(strict=False)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Owner artifact is missing: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Owner artifact is not a JSON object: {path}")
    return payload
