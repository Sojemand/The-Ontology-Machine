"""Semantic release response handlers for the orchestrator contract."""
from __future__ import annotations

from pathlib import Path

from ..assets import build_projection_catalog
from ..runtime_semantic_assets import build_runtime_semantic_assets
from ..semantic_release import default_publish_output_path, publish_semantic_release
from .types import BuildRuntimeSemanticAssetsCommand, PublishSemanticReleaseCommand
from .workflow_errors import error_response


def build_projection_catalog_response(*, root: Path) -> dict:
    try:
        catalog = build_projection_catalog(root)
    except Exception as exc:
        return error_response(str(exc))
    return {"status": "OK", "projection_catalog": catalog.to_dict()}


def build_runtime_semantic_assets_response(command: BuildRuntimeSemanticAssetsCommand) -> dict:
    try:
        runtime_semantic_assets = build_runtime_semantic_assets(command.release)
    except Exception as exc:
        return error_response(str(exc))
    return {"status": "OK", "runtime_semantic_assets": runtime_semantic_assets.to_dict()}


def publish_semantic_release_response(command: PublishSemanticReleaseCommand, *, root: Path) -> dict:
    try:
        kwargs = {
            "release_id": command.release_id,
            "release_version": command.release_version,
            "projection_ids": list(command.projection_ids) or None,
            "materialization_version": command.materialization_version,
        }
        if command.target_locale is not None:
            kwargs["target_locale"] = command.target_locale
        release = publish_semantic_release(root, command.output_path, **kwargs)
    except Exception as exc:
        return error_response(str(exc))
    output_path = command.output_path or default_publish_output_path(
        root,
        release["release_id"],
        release_version=release["release_version"],
        runtime_locale=release.get("runtime_locale"),
    )
    return {
        "status": "OK",
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
            "release_id": release["release_id"],
            "release_version": release["release_version"],
            "release_fingerprint": release["fingerprint"],
        },
        "target_identity_proof": {
            "release_fingerprint": release["fingerprint"],
        },
    }
