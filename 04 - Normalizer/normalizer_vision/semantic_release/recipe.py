"""Persistent semantic-release recipe helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assets import semantic_release_recipe_path
from ..taxonomy_sources import policy as source_policy
from ..models.serialization import atomic_json_write, load_json
from ..taxonomy_compile import source_recipe_defaults
from ..taxonomy_sources import has_source_package, load_source_package
from .policy import budget_semantic_release_file_name
from .types import SemanticReleaseRecipe

RECIPE_FIELDS = (
    "release_id",
    "release_version",
    "projection_ids",
    "materialization_version",
)


def default_recipe(project_root: Path) -> SemanticReleaseRecipe:
    if not has_source_package(project_root):
        raise ValueError("Source-Paket fehlt; semantic_release.recipe kann nur aus dem aktiven Source-Paket abgeleitet werden.")
    return _source_recipe(project_root, materialization_version="1")


def load_recipe(project_root: Path) -> SemanticReleaseRecipe:
    path = semantic_release_recipe_path(project_root)
    if not path.exists():
        return default_recipe(project_root)
    recipe = validate_recipe_payload(project_root, load_json(path))
    if has_source_package(project_root):
        _validate_source_recipe_match(project_root, recipe)
    return recipe


def save_recipe(project_root: Path, payload: dict[str, Any]) -> SemanticReleaseRecipe:
    recipe = validate_recipe_payload(project_root, payload)
    atomic_json_write(semantic_release_recipe_path(project_root), recipe)
    return recipe


def validate_recipe_payload(project_root: Path, payload: dict[str, Any]) -> SemanticReleaseRecipe:
    if not isinstance(payload, dict):
        raise ValueError("normalizer.semantic_release_authoring muss ein JSON-Objekt sein.")
    unknown = sorted(set(payload) - set(RECIPE_FIELDS))
    if unknown:
        raise ValueError(f"semantic_release.recipe enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [field_name for field_name in RECIPE_FIELDS if field_name not in payload]
    if missing:
        raise ValueError(f"semantic_release.recipe enthaelt fehlende Felder: {', '.join(missing)}")
    release_id = source_policy.require_source_id(payload.get("release_id"), label="release_id")
    release_version = _required_string(payload.get("release_version"), field_name="release_version")
    materialization_version = _required_string(
        payload.get("materialization_version"),
        field_name="materialization_version",
    )
    projection_ids = _projection_ids(project_root, payload.get("projection_ids"))
    return {
        "release_id": release_id,
        "release_version": release_version,
        "projection_ids": projection_ids,
        "materialization_version": materialization_version,
    }


def default_publish_output_path(
    project_root: Path,
    release_id: str,
    *,
    release_version: str | None = None,
    runtime_locale: str | None = None,
) -> Path:
    output_root = Path(project_root) / "output"
    return output_root / budget_semantic_release_file_name(
        output_root,
        release_id,
        release_version=release_version,
        runtime_locale=runtime_locale,
    )


def _projection_ids(project_root: Path, value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("projection_ids muss eine Liste von Strings sein.")
    known = _known_projection_ids(project_root)
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"projection_ids[{index}] muss ein String sein.")
        projection_id = item.strip()
        if not projection_id:
            raise ValueError(f"projection_ids[{index}] darf nicht leer sein.")
        if projection_id not in known:
            raise ValueError(f"Lokale Projection nicht gefunden: {projection_id}")
        if projection_id in seen:
            continue
        seen.add(projection_id)
        result.append(projection_id)
    canonical_projection_ids = source_policy.canonical_projection_id_list(
        result,
        label="projection_ids",
    )
    if result != canonical_projection_ids:
        raise ValueError("projection_ids muss kanonisch nach projection_id sortiert sein.")
    return canonical_projection_ids


def _required_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} muss ein nicht-leerer String sein.")
    return value.strip()


def _known_projection_ids(project_root: Path) -> set[str]:
    if not has_source_package(project_root):
        raise ValueError("Source-Paket fehlt; projection_ids koennen nur aus dem aktiven Source-Paket abgeleitet werden.")
    return set(load_source_package(project_root)["release"]["projection_ids"])


def _source_recipe(project_root: Path, *, materialization_version: str) -> SemanticReleaseRecipe:
    package = load_source_package(project_root)
    return source_recipe_defaults(
        package["release"],
        materialization_version=materialization_version,
    )


def _validate_source_recipe_match(project_root: Path, recipe: SemanticReleaseRecipe) -> None:
    expected = _source_recipe(project_root, materialization_version=recipe["materialization_version"])
    drift = [
        field_name
        for field_name in ("release_id", "release_version", "projection_ids")
        if recipe[field_name] != expected[field_name]
    ]
    if drift:
        raise ValueError(f"semantic_release.recipe driftet vom Source-Paket ab: {', '.join(drift)}")


__all__ = [
    "RECIPE_FIELDS",
    "default_publish_output_path",
    "default_recipe",
    "load_recipe",
    "save_recipe",
    "validate_recipe_payload",
]
