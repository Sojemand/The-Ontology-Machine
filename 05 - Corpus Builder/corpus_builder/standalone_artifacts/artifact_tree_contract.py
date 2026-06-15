from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import owner_ok, path_hash

_REQUIRED_FOLDERS = (
    "Input",
    "Corpus",
    "Semantic Release",
    "Documents/logs",
    "Documents/normalized",
    "Documents/originals",
    "Documents/page_images",
    "Documents/raw_extracts",
    "Documents/requests",
    "Documents/structured",
    "Documents/validation",
    "Error Cases",
)


def validate_artifact_tree(payload: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(str(payload.get("artifact_root_path") or ""))
    if not root.exists():
        raise ValueError("artifact_root_path does not exist.")
    missing = [item for item in _REQUIRED_FOLDERS if not (root / item).exists()]
    errors = [f"required_path_is_file:{item}" for item in _REQUIRED_FOLDERS if (root / item).exists() and not (root / item).is_dir()]
    output = {
        "is_valid": not missing and not errors,
        "artifact_root_path_hash": path_hash(root),
        "canonical_folder_map": {
            "artifact_root_path": str(root.resolve(strict=False)),
            "input_path": str((root / "Input").resolve(strict=False)),
            "corpus_path": str((root / "Corpus").resolve(strict=False)),
            "documents_path": str((root / "Documents").resolve(strict=False)),
            "error_cases_path": str((root / "Error Cases").resolve(strict=False)),
            "semantic_release_path": str((root / "Semantic Release").resolve(strict=False)),
        },
        "missing_paths": missing,
        "created_paths": [],
        "unexpected_paths": [],
        "validation_errors": errors,
        "folder_contract_fingerprint": path_hash(root),
    }
    return owner_ok(
        owner_action="validate_artifact_tree",
        capability="artifact_tree_contract_hardening",
        target_identity=_mapping(payload, "target_identity"),
        output_refs=output,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "validate_artifact_tree",
            "artifact_root_path_hash": output["artifact_root_path_hash"],
        },
        diagnostics=[{"code": item} for item in errors],
    )


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}
