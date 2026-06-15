"""Workflow orchestration for semantic release publishing."""
from __future__ import annotations

from pathlib import Path

from ..models.serialization import utc_now_iso
from ..runtime_semantic_assets import build_runtime_semantic_assets
from ..taxonomy_sources import policy as source_policy
from ..taxonomy_sources import has_source_package, load_source_package
from ..taxonomy import (
    SEMANTIC_RELEASE_SCHEMA_VERSION,
    projection_surface_signals,
)
from ..taxonomy_compile import compile_source_package
from . import adapter, policy
from .shared_identity import build_master_taxonomy_release_id
from .recipe import default_publish_output_path, load_recipe
from .types import SemanticReleasePayload


def build_semantic_release(
    project_root: Path,
    *,
    release_id: str | None = None,
    release_version: str | None = None,
    projection_ids: list[str] | None = None,
    materialization_version: str | None = None,
    target_locale: str | None = None,
) -> SemanticReleasePayload:
    recipe = load_recipe(project_root)
    effective_release_id = source_policy.require_source_id(
        str(release_id or recipe["release_id"]).strip() or "semantic_release.default",
        label="release_id",
    )
    effective_release_version = str(release_version or recipe["release_version"]).strip() or "1"
    effective_projection_ids = source_policy.canonical_projection_id_list(
        list(projection_ids) if projection_ids is not None else list(recipe["projection_ids"]),
        label="projection_ids",
    )
    effective_materialization_version = str(materialization_version or recipe["materialization_version"]).strip() or "1"
    if not has_source_package(project_root):
        raise ValueError("Source-Paket fehlt; semantic releases koennen nur aus dem aktiven Source-Paket gebaut werden.")
    source_package = load_source_package(project_root)
    return build_semantic_release_from_source_package(
        source_package,
        release_id=effective_release_id,
        release_version=effective_release_version,
        projection_ids=effective_projection_ids,
        materialization_version=effective_materialization_version,
        target_locale=target_locale,
    )


def build_semantic_release_from_source_package(
    source_package: dict[str, object],
    *,
    release_id: str,
    release_version: str,
    projection_ids: list[str],
    materialization_version: str,
    target_locale: str | None = None,
) -> SemanticReleasePayload:
    compiled = compile_source_package(
        source_package,
        projection_ids=projection_ids,
        target_locale=target_locale,
    )
    payload = build_semantic_release_core_from_compiled(
        source_package,
        compiled,
        release_id=release_id,
        release_version=release_version,
        materialization_version=materialization_version,
    )
    runtime_assets = build_runtime_semantic_assets(payload).to_dict()
    payload["projection_catalog"] = runtime_assets["projection_catalog"]
    payload["runtime_semantic_assets"] = runtime_assets
    return payload


def build_semantic_release_core_from_compiled(
    source_package: dict[str, object],
    compiled,
    *,
    release_id: str,
    release_version: str,
    materialization_version: str,
) -> SemanticReleasePayload:
    master = compiled.master
    selected_ids = list(compiled.release["projection_ids"])
    projections = [compiled.projections[projection_id] for projection_id in selected_ids]
    runtime_locale = str(compiled.release["runtime_locale"] or "").strip()
    master_taxonomy_release_id = build_master_taxonomy_release_id(source_package["master"]["core"])
    for index, projection in enumerate(projections):
        projection_surface_signals(
            projection,
            required=True,
            field_name=f"projections[{index}].routing.surface_signals",
        )

    payload: SemanticReleasePayload = {
        "schema_version": SEMANTIC_RELEASE_SCHEMA_VERSION,
        "release_id": release_id,
        "release_version": release_version,
        "master_taxonomy_id": master.get("taxonomy_id"),
        "master_taxonomy_version": master.get("taxonomy_version"),
        "master_taxonomy_release_id": master_taxonomy_release_id,
        "runtime_locale": runtime_locale,
        "projection_ids": selected_ids,
        "materialization_version": materialization_version,
        "created_at": utc_now_iso(),
        "fingerprint": "",
        "master_taxonomy": master,
        "projections": projections,
        "analysis": policy.analyze_taxonomy_shape(master, projections),
    }
    payload["fingerprint"] = policy.build_release_fingerprint(payload)
    return payload


def publish_semantic_release(
    project_root: Path,
    output_path: Path | None = None,
    *,
    release_id: str | None = None,
    release_version: str | None = None,
    projection_ids: list[str] | None = None,
    materialization_version: str | None = None,
    target_locale: str | None = None,
) -> SemanticReleasePayload:
    release = build_semantic_release(
        project_root,
        release_id=release_id,
        release_version=release_version,
        projection_ids=projection_ids,
        materialization_version=materialization_version,
        target_locale=target_locale,
    )
    target_path = Path(output_path) if output_path is not None else default_publish_output_path(
        project_root,
        release["release_id"],
        release_version=release["release_version"],
        runtime_locale=release["runtime_locale"],
    )
    adapter.save_semantic_release(target_path, release)
    return release
