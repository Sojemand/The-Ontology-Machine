from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter import owner_response
from .policy import canonical_folder_map, canonical_path, is_within, path_hash
from .types import ARTIFACT_TREE_FOLDERS, KERNEL_ARTIFACT_TREE_VERSION
from .validation import validate_check_request, validate_create_request


def create_artifact_tree(payload: dict[str, Any]) -> dict[str, Any]:
    request = validate_create_request(payload)
    root = Path(canonical_path(Path(str(request["artifact_root_parent"])) / str(request["artifact_root_name"])))
    target_identity = _mapping(request, "target_identity")
    expected_hash = str(request.get("expected_artifact_root_path_hash") or "")
    if not root.is_absolute():
        raise ValueError("artifact root must resolve to an absolute path.")
    existing = root.exists()
    if existing and request["create_mode"] == "create_new":
        raise ValueError("artifact root already exists.")
    created_paths: list[str] = []
    verified_paths: list[str] = []
    already_existing_paths: list[str] = []
    if not request.get("dry_run"):
        root.mkdir(parents=True, exist_ok=True)
    for relative in ARTIFACT_TREE_FOLDERS:
        folder = root / relative
        if not is_within(root, folder):
            raise ValueError("created path escapes artifact root.")
        if folder.exists():
            if not folder.is_dir():
                raise ValueError(f"required folder is a file: {folder}")
            already_existing_paths.append(str(folder))
        else:
            if not request.get("dry_run"):
                folder.mkdir(parents=True, exist_ok=True)
            created_paths.append(str(folder))
        verified_paths.append(str(folder))
    root_hash = path_hash(root)
    if expected_hash and expected_hash != root_hash:
        raise ValueError("expected_artifact_root_path_hash does not match resolved root.")
    if target_identity.get("artifact_root_path_hash") and target_identity["artifact_root_path_hash"] != root_hash:
        raise ValueError("target identity artifact_root_path_hash does not match resolved root.")
    folders = canonical_folder_map(root)
    output = {
        "folder_contract_version": KERNEL_ARTIFACT_TREE_VERSION,
        "artifact_root_path_hash": root_hash,
        "created_paths": created_paths,
        "verified_paths": verified_paths,
        "already_existing_paths": already_existing_paths,
        **folders,
    }
    return owner_response(
        owner_action="create_artifact_tree",
        capability="artifact_tree_contract_hardening",
        target_identity=target_identity,
        output_refs=output,
        target_identity_proof={
            "artifact_root_path": folders["artifact_root_path"],
            "artifact_root_path_hash": root_hash,
            "folder_contract_version": KERNEL_ARTIFACT_TREE_VERSION,
        },
        receipt_fields={
            "owner_module": "00 - Orchestrator",
            "owner_action": "create_artifact_tree",
            "artifact_root_path_hash": root_hash,
            "folder_contract_version": KERNEL_ARTIFACT_TREE_VERSION,
        },
        summary="Artifact Tree contract created or verified.",
    )


def validate_artifact_tree(payload: dict[str, Any]) -> dict[str, Any]:
    request = validate_check_request(payload)
    root = Path(canonical_path(str(request["artifact_root_path"])))
    target_identity = _mapping(request, "target_identity")
    if not root.exists():
        raise ValueError("artifact root does not exist.")
    if not root.is_dir():
        raise ValueError("artifact root must be a directory.")
    root_hash = path_hash(root)
    if target_identity.get("artifact_root_path_hash") and target_identity["artifact_root_path_hash"] != root_hash:
        raise ValueError("target identity artifact_root_path_hash does not match resolved root.")
    missing_paths: list[str] = []
    unexpected_paths: list[str] = []
    created_paths: list[str] = []
    validation_errors: list[str] = []
    for relative in ARTIFACT_TREE_FOLDERS:
        folder = root / relative
        if not folder.exists():
            missing_paths.append(relative)
        elif not folder.is_dir():
            validation_errors.append(f"required_path_is_file:{relative}")
    if request.get("return_unexpected_paths"):
        allowed = {relative.replace("\\", "/") for relative in ARTIFACT_TREE_FOLDERS}
        for path in root.rglob("*"):
            if not path.is_dir():
                continue
            relative = path.relative_to(root).as_posix()
            if relative and relative not in allowed and not any(item.startswith(relative + "/") for item in allowed):
                unexpected_paths.append(relative)
    if request.get("require_empty_input") and any((root / "Input").iterdir()):
        validation_errors.append("input_not_empty")
    folders = canonical_folder_map(root)
    output = {
        "is_valid": not missing_paths and not validation_errors,
        "artifact_root_path_hash": root_hash,
        "missing_paths": missing_paths,
        "created_paths": created_paths,
        "unexpected_paths": unexpected_paths,
        "validation_errors": validation_errors,
        "folder_contract_fingerprint": path_hash(root),
        **folders,
    }
    return owner_response(
        owner_action="validate_artifact_tree",
        capability="artifact_tree_contract_hardening",
        target_identity=target_identity,
        output_refs=output,
        target_identity_proof={
            "artifact_root_path": folders["artifact_root_path"],
            "artifact_root_path_hash": root_hash,
            "folder_contract_version": KERNEL_ARTIFACT_TREE_VERSION,
        },
        receipt_fields={
            "owner_module": "00 - Orchestrator",
            "owner_action": "validate_artifact_tree",
            "artifact_root_path_hash": root_hash,
            "folder_contract_fingerprint": output["folder_contract_fingerprint"],
        },
        diagnostics=[{"code": error} for error in validation_errors],
        summary="Artifact Tree contract validated.",
    )


def _mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, dict) else {}
