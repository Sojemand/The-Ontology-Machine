"""Default-blueprint and zero-shot release response handlers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..semantic_release import build_semantic_release_from_source_package, default_publish_output_path, save_semantic_release
from ..source_authoring import operations as source_operations
from ..taxonomy_sources import source_package_paths_for_root
from ..taxonomy_sources.adapter import load_yaml_mapping
from ..taxonomy_sources.validation import validate_source_package
from .types import CreateZeroShotWorkingReleaseCommand, ExportDefaultBlueprintReleaseCommand
from .workflow_errors import error_response

BLUEPRINT_ROOT_RELATIVE_PATH = Path("config") / "taxonomy_blueprints"


def list_default_blueprints_response(*, root: Path) -> dict:
    return {"status": "OK", "blueprints": [_blueprint_descriptor(root, path) for path in _discover_blueprint_roots(root)]}


def export_default_blueprint_release_response(command: ExportDefaultBlueprintReleaseCommand, *, root: Path) -> dict:
    blueprint_root = _require_blueprint_root(root, command.blueprint_ref)
    blueprint = _blueprint_descriptor(root, blueprint_root)
    package = _load_blueprint_package(blueprint_root)
    release = build_semantic_release_from_source_package(
        package,
        release_id=str(package["release"]["release_id"]),
        release_version=str(package["release"]["release_version"]),
        projection_ids=list(package["release"]["projection_ids"]),
        materialization_version="1",
        target_locale=command.target_locale,
    )
    output_path = command.output_path or default_publish_output_path(
        root,
        release["release_id"],
        release_version=release["release_version"],
        runtime_locale=release.get("runtime_locale"),
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    save_semantic_release(Path(output_path), release)
    release_ref = _default_release_ref(release)
    return {
        "status": "OK",
        "blueprint_ref": command.blueprint_ref,
        "blueprint": blueprint,
        "output_path": str(output_path),
        "release_id": release["release_id"],
        "release_version": release["release_version"],
        "projection_ids": list(release["projection_ids"]),
        "fingerprint": release["fingerprint"],
        "runtime_locale": release.get("runtime_locale"),
        "master_taxonomy_release_id": release.get("master_taxonomy_release_id"),
        "output_refs": {
            "output_path": str(output_path),
            "release_path": str(output_path),
            "release_id": release_ref["release_id"],
            "release_version": release_ref["release_version"],
            "release_fingerprint": release_ref["release_fingerprint"],
            "release_ref": release_ref,
        },
        "target_identity_proof": {
            "release_fingerprint": release_ref["release_fingerprint"],
        },
    }


def create_zero_shot_working_release_response(command: CreateZeroShotWorkingReleaseCommand, *, root: Path) -> dict:
    try:
        derive_payload = {
            "blueprint_ref": command.blueprint_ref,
            "target_release_id": command.target_release_id,
            "target_release_version": command.target_release_version,
        }
        derived = source_operations.derive_working_release_from_blueprint(root, derive_payload)
        locale_payload = {"target_locale": command.target_locale} if command.target_locale is not None else {}
        compiled = source_operations.compile_release_package(root, locale_payload)
        export_payload = dict(locale_payload)
        if command.output_path is not None:
            export_payload["output_path"] = str(command.output_path)
        exported = source_operations.export_semantic_release(root, export_payload)
    except Exception as exc:
        return error_response(str(exc))
    return {
        "status": "OK",
        "blueprint_ref": command.blueprint_ref,
        "derived_working_release": derived,
        "compiled_release": compiled,
        "exported_release": exported,
        "output_path": exported.get("output_path"),
        "runtime_locale": exported.get("runtime_locale"),
    }


def _discover_blueprint_roots(project_root: Path) -> list[Path]:
    root = project_root / BLUEPRINT_ROOT_RELATIVE_PATH
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "blueprint.yaml").exists())


def _require_blueprint_root(project_root: Path, blueprint_ref: str) -> Path:
    target = str(blueprint_ref or "").strip()
    for root in _discover_blueprint_roots(project_root):
        metadata = _load_blueprint_metadata(root)
        if str(metadata.get("blueprint_ref") or "").strip() == target:
            return root
    raise ValueError(f"Blueprint nicht gefunden: {target}")


def _load_blueprint_metadata(root: Path) -> dict[str, Any]:
    payload = load_yaml_mapping(root / "blueprint.yaml", label="blueprint")
    if str(payload.get("blueprint_ref") or "").strip() != root.name:
        raise ValueError(f"blueprint.blueprint_ref stimmt nicht mit dem Ordnernamen ueberein: {root.name}")
    return payload


def _load_blueprint_package(root: Path) -> dict[str, object]:
    return validate_source_package(source_package_paths_for_root(root / "source_package"))


def _blueprint_descriptor(project_root: Path, root: Path) -> dict[str, Any]:
    metadata = _load_blueprint_metadata(root)
    package = _load_blueprint_package(root)
    release = package["release"]
    return {
        "blueprint_ref": str(metadata["blueprint_ref"]),
        "label": str(metadata.get("label") or "").strip(),
        "description": str(metadata.get("description") or "").strip(),
        "kind": str(metadata.get("kind") or "").strip(),
        "immutable": bool(metadata.get("immutable", True)),
        "primary_locale": str(metadata.get("primary_locale") or "").strip(),
        "release_id": str(release["release_id"]),
        "release_version": str(release["release_version"]),
        "available_locales": list(release["available_locales"]),
        "default_runtime_locale": str(release["default_runtime_locale"]),
        "projection_count": len(release["projection_ids"]),
        "projection_ids": list(release["projection_ids"]),
        "source_path": str((root / "source_package").relative_to(project_root).as_posix()),
    }


def _default_release_ref(release: dict[str, Any]) -> dict[str, Any]:
    master = release.get("master_taxonomy") if isinstance(release.get("master_taxonomy"), dict) else {}
    taxonomy_fingerprint = str(
        release.get("master_taxonomy_release_id")
        or master.get("taxonomy_fingerprint")
        or _stable_hash(master)
    )
    projection_refs = []
    projections = release.get("projections") if isinstance(release.get("projections"), list) else []
    for index, projection in enumerate(projections, start=1):
        if not isinstance(projection, dict):
            continue
        projection_id = str(projection.get("projection_id") or projection.get("id") or f"default.projection.{index}")
        projection_refs.append(
            {
                "projection_id": projection_id,
                "projection_fingerprint": str(
                    projection.get("projection_fingerprint")
                    or projection.get("fingerprint")
                    or _stable_hash(projection)
                ),
            }
        )
    if not projection_refs:
        for projection_id in release.get("projection_ids", []):
            if projection_id:
                projection_refs.append(
                    {
                        "projection_id": str(projection_id),
                        "projection_fingerprint": _stable_hash(str(projection_id)),
                    }
                )
    return {
        "release_id": str(release.get("release_id") or ""),
        "release_version": str(release.get("release_version") or ""),
        "release_fingerprint": str(release.get("fingerprint") or release.get("release_fingerprint") or ""),
        "taxonomy_ref": {
            "taxonomy_id": str(
                release.get("master_taxonomy_release_id")
                or release.get("master_taxonomy_id")
                or master.get("taxonomy_id")
                or "default.taxonomy"
            ),
            "taxonomy_fingerprint": taxonomy_fingerprint,
            "runtime_locale": str(release.get("runtime_locale") or ""),
        },
        "projection_refs": projection_refs,
    }


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
