from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from tests.fixtures.taxonomy_refactor_baseline import normalize_phase0_release_payload


def artifact_paths(
    *,
    optimizer_fixture_path: str | Path,
    corpus_release_path: str | Path,
    corpus_active_release_path: str | Path,
    corpus_stage_release_path: str | Path,
) -> dict[str, object]:
    return {
        "optimizer_fixture_path": Path(optimizer_fixture_path),
        "release_paths": [
            Path(corpus_release_path),
            Path(corpus_active_release_path),
            Path(corpus_stage_release_path),
        ],
    }


def canonical_release_payload(expected_release: dict[str, Any], release_paths: list[Path]) -> dict[str, Any]:
    expected_view = normalize_phase0_release_payload(expected_release)
    for path in release_paths:
        existing = load_optional_json(path)
        if isinstance(existing, dict) and normalize_phase0_release_payload(existing) == expected_view:
            return existing
    return expected_release


def project_optimizer_runtime_payload(
    runtime_payload: dict[str, Any],
    *,
    reference_fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    projected = copy.deepcopy(runtime_payload)
    bundle = projected.get("vision_policy_bundle")
    if isinstance(bundle, dict):
        bundle.pop("semantic_extraction_policy", None)
        ocr_policy = bundle.get("ocr_policy")
        if isinstance(ocr_policy, dict):
            ocr_policy.pop("projection_overrides", None)
    projection_catalog = projected.get("projection_catalog")
    if not isinstance(projection_catalog, dict):
        return projected
    reference_ids = reference_projection_ids(reference_fixture_path)
    if not reference_ids:
        return projected
    live_entries = {
        str(entry.get("projection_id") or ""): entry
        for entry in projection_catalog.get("projections", [])
        if isinstance(entry, dict) and str(entry.get("projection_id") or "")
    }
    projection_catalog["projections"] = [
        copy.deepcopy(live_entries[projection_id])
        for projection_id in reference_ids
        if projection_id in live_entries
    ]
    return projected


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def reference_projection_ids(path: str | Path | None) -> list[str]:
    if path is None:
        return []
    payload = load_optional_json(Path(path))
    if not isinstance(payload, dict):
        return []
    projection_catalog = payload.get("projection_catalog")
    if not isinstance(projection_catalog, dict):
        return []
    result: list[str] = []
    for entry in projection_catalog.get("projections", []):
        if not isinstance(entry, dict):
            continue
        projection_id = str(entry.get("projection_id") or "").strip()
        if projection_id:
            result.append(projection_id)
    return result


def load_required_json(path: Path) -> dict[str, Any]:
    payload = load_optional_json(path)
    if payload is None:
        raise AssertionError(f"Expected a JSON object at {path}")
    return payload


def write_json_if_changed(path: Path, payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True
