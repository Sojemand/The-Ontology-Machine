from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable

from .contract_client import _runtime_env, invoke_endpoint, invoke_product_contract, module_spec
from .governance import ADMIN_ENDPOINTS, EDIT_ENDPOINTS, PRODUCT_ACTIONS
from .tool_handler_path_checks import _ensure_path_budget
from .tool_handler_pipeline_store import _write_json_file
from .tool_handler_runtime_state import WORKSPACE_NORMALIZER_AUTHORING_DIR
from .tool_handler_types import ToolFailure

def _invoke_product(module_key: str, payload: dict[str, Any], *, timeout: int | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"allowed_actions": PRODUCT_ACTIONS[module_key]}
    if timeout is not None:
        kwargs["timeout"] = timeout
    return invoke_product_contract(module_key, payload, **kwargs)


def _invoke_edit(
    module_key: str,
    payload: dict[str, Any],
    *,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    return invoke_endpoint(EDIT_ENDPOINTS[module_key], payload, env_overrides=env_overrides)


def _invoke_workspace_normalizer_edit(artifact_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    home = _ensure_workspace_normalizer_home(artifact_path)
    return _invoke_edit("normalizer", payload, env_overrides=_workspace_normalizer_env(home))


def _invoke_workspace_normalizer_read(artifact_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    home = _workspace_normalizer_home(artifact_path)
    return _invoke_edit("normalizer", payload, env_overrides=_workspace_normalizer_env(home))


def _normalizer_edit_invoker(artifact_folder: str | None) -> Callable[[dict[str, Any]], dict[str, Any]]:
    if not artifact_folder:
        return lambda payload: _invoke_edit("normalizer", payload)
    artifact_path = Path(artifact_folder).expanduser().resolve()
    return lambda payload: _invoke_workspace_normalizer_edit(artifact_path, payload)


def _normalizer_read_invoker(artifact_folder: str | None) -> Callable[[dict[str, Any]], dict[str, Any]]:
    if not artifact_folder:
        return lambda payload: _invoke_edit("normalizer", payload)
    artifact_path = Path(artifact_folder).expanduser().resolve()
    return lambda payload: _invoke_workspace_normalizer_read(artifact_path, payload)


def _workspace_normalizer_home(artifact_path: Path) -> Path:
    return artifact_path / WORKSPACE_NORMALIZER_AUTHORING_DIR


def _workspace_normalizer_env(home: Path) -> dict[str, str]:
    return {"NORMALIZER_VISION_HOME": str(home)}


def _ensure_workspace_normalizer_home(artifact_path: Path) -> Path:
    _ensure_path_budget(artifact_path, "artifact_folder")
    normalizer_root = module_spec("normalizer").root
    home = _workspace_normalizer_home(artifact_path)
    _ensure_path_budget(home, "Workspace-Normalizer-Home")
    copy_relatives = (
        Path("module-manifest.json"),
        Path("config") / "config.yaml",
        Path("config") / "prompt_bundle.json",
        Path("config") / "prompt_overrides.json",
        Path("config") / "taxonomy_blueprints",
    )
    for relative in copy_relatives:
        _ensure_copy_path_budget(normalizer_root / relative, home / relative)
    artifact_path.mkdir(parents=True, exist_ok=True)
    config_dir = home / "config"
    _ensure_path_budget(config_dir, "Workspace-Normalizer-Config")
    config_dir.mkdir(parents=True, exist_ok=True)

    for relative in copy_relatives:
        _copy_path_if_missing(normalizer_root / relative, home / relative)
    _ensure_workspace_default_source_package(home, normalizer_root)
    return home


def _ensure_workspace_default_source_package(home: Path, normalizer_root: Path) -> None:
    config_dir = home / "config"
    recipe_path = config_dir / "semantic_release.recipe.json"
    sources_root = config_dir / "taxonomy_sources"
    _ensure_path_budget(sources_root, "Workspace-Normalizer-Sources")
    _ensure_path_budget(recipe_path, "Workspace-Normalizer-Recipe")
    sources_root.mkdir(parents=True, exist_ok=True)
    release_id = _read_recipe_release_id(recipe_path)
    if release_id:
        active_source = sources_root / release_id
        if active_source.exists():
            return
        if release_id != "semantic_release.default":
            raise ToolFailure(
                "Workspace-Normalizer-Authoring ist unvollstaendig: "
                f"Source-Paket fehlt fuer {release_id} unter {active_source}."
            )

    blueprint_root = normalizer_root / "config" / "taxonomy_blueprints" / "default" / "source_package"
    target_root = sources_root / "semantic_release.default"
    _ensure_copy_path_budget(blueprint_root, target_root)
    _copy_path_if_missing(blueprint_root, target_root)
    summary = _read_blueprint_release_summary(blueprint_root / "release.yaml")
    _write_json_file(
        recipe_path,
        {
            "release_id": summary["release_id"],
            "release_version": summary["release_version"],
            "projection_ids": summary["projection_ids"],
            "materialization_version": "1",
        },
    )


def _copy_path_if_missing(source: Path, target: Path) -> None:
    _ensure_copy_path_budget(source, target)
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
        return
    shutil.copy2(source, target)


def _ensure_copy_path_budget(source: Path, target: Path) -> None:
    _ensure_path_budget(target, "Workspace-Normalizer-Zielpfad")
    if not source.is_dir():
        return
    for child in source.rglob("*"):
        _ensure_path_budget(target / child.relative_to(source), "Workspace-Normalizer-Zielpfad")


def _read_recipe_release_id(recipe_path: Path) -> str:
    if not recipe_path.exists():
        return ""
    try:
        payload = json.loads(recipe_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return ""
    return str(payload.get("release_id") or "").strip()


def _read_blueprint_release_summary(release_path: Path) -> dict[str, Any]:
    release_id = "semantic_release.default"
    release_version = ""
    projection_ids: list[str] = []
    in_projection_ids = False
    for raw_line in release_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("release_id:"):
            release_id = line.split(":", 1)[1].strip() or release_id
            in_projection_ids = False
        elif line.startswith("release_version:"):
            release_version = line.split(":", 1)[1].strip()
            in_projection_ids = False
        elif line.startswith("projection_ids:"):
            in_projection_ids = True
        elif in_projection_ids and line.startswith("- "):
            projection_ids.append(line[2:].strip())
        elif not raw_line.startswith((" ", "\t", "-")):
            in_projection_ids = False
    return {"release_id": release_id, "release_version": release_version, "projection_ids": projection_ids}


def _invoke_admin(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    return invoke_endpoint(ADMIN_ENDPOINTS[module_key], payload)

__all__ = [name for name in globals() if not name.startswith("__")]
