"""Load and persist the active locale-aware taxonomy source package."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from ..models.serialization import atomic_text_write
from ..semantic_release.recipe import load_recipe, save_recipe
from ..taxonomy_compile import source_recipe_defaults
from ..taxonomy_sources import policy as source_policy
from ..taxonomy_sources import active_source_package_paths, load_source_package, validate_source_package_payload
from ..taxonomy_sources.governance import sync_release_governance


def load_context(project_root: Path) -> dict[str, Any]:
    package = deepcopy(load_source_package(project_root))
    recipe = load_recipe(project_root)
    return {
        "paths": package.pop("paths"),
        "package": package,
        "materialization_version": str(recipe["materialization_version"]),
    }


def save_context(project_root: Path, package: dict[str, Any], *, materialization_version: str | None = None) -> dict[str, Any]:
    payload = deepcopy(package)
    payload["release"] = sync_release_governance(
        payload["release"],
        glossary_locales=sorted(payload.get("glossaries", {})),
    )
    validated = validate_source_package_payload(payload)
    effective_materialization_version = str(materialization_version or load_materialization_version(project_root)).strip() or "1"
    current_root = active_source_package_paths(project_root).root
    target_root = _target_root(current_root, validated["release"]["release_id"])
    _prepare_root(current_root, target_root)
    _write_yaml(target_root / "release.yaml", validated["release"])
    _write_yaml(target_root / "master.core.yaml", validated["master"]["core"])
    _sync_locale_files(
        target_root,
        validated["release"]["available_locales"],
        validated["master"]["texts"],
        validated.get("glossaries", {}),
    )
    _sync_projection_files(
        target_root,
        validated["release"]["projection_ids"],
        validated["release"]["available_locales"],
        validated["projections"],
    )
    save_recipe(
        project_root,
        source_recipe_defaults(
            validated["release"],
            materialization_version=effective_materialization_version,
        ),
    )
    return validated


def load_materialization_version(project_root: Path) -> str:
    return str(load_recipe(project_root)["materialization_version"])


def empty_like(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: empty_like(child) for key, child in value.items()}
    if isinstance(value, list):
        return []
    if isinstance(value, bool):
        return False
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    return ""


def _target_root(current_root: Path, release_id: str) -> Path:
    release = source_policy.require_source_id(release_id, label="release.release_id")
    return current_root.parent / release


def _prepare_root(current_root: Path, target_root: Path) -> None:
    if current_root == target_root:
        target_root.mkdir(parents=True, exist_ok=True)
        return
    if target_root.exists():
        raise ValueError(f"Source-Paket existiert bereits: {target_root.name}")
    current_root.rename(target_root)


def _sync_locale_files(
    root: Path,
    available_locales: list[str],
    master_texts: dict[str, dict[str, Any]],
    glossaries: dict[str, dict[str, Any]],
) -> None:
    keep = set()
    for locale in available_locales:
        master_text_path = root / f"master.text.{locale}.yaml"
        _write_yaml(master_text_path, master_texts[locale])
        keep.add(master_text_path.name)
        glossary_payload = glossaries.get(locale)
        glossary_path = root / f"translation_glossary.{locale}.yaml"
        if glossary_payload and glossary_payload.get("glossary"):
            _write_yaml(glossary_path, glossary_payload)
            keep.add(glossary_path.name)
        else:
            glossary_path.unlink(missing_ok=True)
    for path in root.glob("master.text.*.yaml"):
        if path.name not in keep:
            path.unlink(missing_ok=True)
    for path in root.glob("translation_glossary.*.yaml"):
        if path.name not in keep:
            path.unlink(missing_ok=True)


def _sync_projection_files(
    root: Path,
    projection_ids: list[str],
    available_locales: list[str],
    projections: dict[str, dict[str, Any]],
) -> None:
    projection_root = root / "projections"
    projection_root.mkdir(parents=True, exist_ok=True)
    keep = set()
    for projection_id in projection_ids:
        file_projection_id = source_policy.require_source_id(projection_id, label="projection_id")
        keep.add(f"{file_projection_id}.core.yaml")
        _write_yaml(
            projection_root / f"{file_projection_id}.core.yaml",
            projections[projection_id]["core"],
        )
        for locale in available_locales:
            file_name = f"{file_projection_id}.text.{locale}.yaml"
            keep.add(file_name)
            _write_yaml(
                projection_root / file_name,
                projections[projection_id]["texts"][locale],
            )
    for path in projection_root.glob("*.yaml"):
        if path.name not in keep:
            path.unlink(missing_ok=True)


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    atomic_text_write(
        path,
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
    )
