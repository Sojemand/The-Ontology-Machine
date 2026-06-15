"""Named contract types shared between subprocess stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

NORMALIZE_DOCUMENT_ACTION = "normalize_document"
BUILD_PROJECTION_CATALOG_ACTION = "build_projection_catalog"
BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION = "build_runtime_semantic_assets"
PUBLISH_SEMANTIC_RELEASE_ACTION = "publish_semantic_release"
LIST_DEFAULT_BLUEPRINTS_ACTION = "list_default_blueprints"
EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION = "export_default_blueprint_release"
CREATE_ZERO_SHOT_WORKING_RELEASE_ACTION = "create_zero_shot_working_release"
HEALTHCHECK_ACTION = "healthcheck"
DEBUG_RUN_ACTION = "debug_run"
ActionName = Literal[
    "normalize_document",
    "build_projection_catalog",
    "build_runtime_semantic_assets",
    "publish_semantic_release",
    "list_default_blueprints",
    "export_default_blueprint_release",
    "create_zero_shot_working_release",
    "healthcheck",
    "debug_run",
]


@dataclass(frozen=True)
class RuntimeSettings:
    model: str
    max_output_tokens: int


@dataclass(frozen=True)
class NormalizeDocumentCommand:
    structured_path: Path
    normalized_output_path: Path
    request_output_path: Path | None
    runtime_settings: RuntimeSettings
    release: dict[str, Any] | None = None


@dataclass(frozen=True)
class HealthcheckCommand:
    runtime_settings: RuntimeSettings


@dataclass(frozen=True)
class PublishSemanticReleaseCommand:
    release_id: str | None = None
    release_version: str | None = None
    projection_ids: tuple[str, ...] = ()
    materialization_version: str | None = None
    target_locale: str | None = None
    output_path: Path | None = None


@dataclass(frozen=True)
class ExportDefaultBlueprintReleaseCommand:
    blueprint_ref: str
    target_locale: str | None = None
    output_path: Path | None = None


@dataclass(frozen=True)
class CreateZeroShotWorkingReleaseCommand:
    blueprint_ref: str
    target_release_id: str | None = None
    target_release_version: str | None = None
    target_locale: str | None = None
    output_path: Path | None = None


@dataclass(frozen=True)
class BuildRuntimeSemanticAssetsCommand:
    release: dict[str, Any]


@dataclass(frozen=True)
class DebugRunCommand:
    mode: Literal["single", "batch"]
    session_root: Path
    output_root: Path
    runtime_settings: RuntimeSettings
    source_path: Path | None = None
    input_root: Path | None = None
    worker_count: int | None = None
