"""Blueprint source-authoring operations."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..taxonomy_sources import source_package_paths_for_root
from ..taxonomy_sources.adapter import load_yaml_mapping
from ..taxonomy_sources.validation import validate_source_package
from . import adapter
from .operation_common import optional_text, required_text
from .response import build_response

BLUEPRINT_ROOT_RELATIVE_PATH = Path("config") / "taxonomy_blueprints"


def list_default_blueprints(project_root) -> dict[str, object]:
    blueprints = [_blueprint_descriptor(project_root, root) for root in _discover_blueprint_roots(project_root)]
    return build_response(
        "list_default_blueprints",
        headline="Default blueprints available",
        summary_lines=[
            f"Blueprints: {len(blueprints)}",
            f"Primary locales: {', '.join(item['primary_locale'] for item in blueprints)}",
        ],
        references_existing_codes=[item["blueprint_ref"] for item in blueprints],
        blueprints=blueprints,
        compile_effect="Reading blueprint metadata does not change saved source files or release state.",
        prompt_effect="Blueprint discovery only reports immutable start points for later derive steps.",
        corpus_effect="No corpus-visible change exists until a blueprint is derived, compiled, exported, and activated.",
    )


def derive_working_release_from_blueprint(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    current_release = context["package"]["release"]
    blueprint_ref = required_text(payload.get("blueprint_ref"), label="blueprint_ref")
    blueprint_root = _require_blueprint_root(project_root, blueprint_ref)
    blueprint = _blueprint_descriptor(project_root, blueprint_root)
    package = deepcopy(_load_blueprint_package(blueprint_root))
    package["release"]["release_id"] = optional_text(
        payload.get("target_release_id"),
        label="target_release_id",
    ) or str(current_release["release_id"])
    package["release"]["release_version"] = optional_text(
        payload.get("target_release_version"),
        label="target_release_version",
    ) or str(current_release["release_version"])
    saved = adapter.save_context(project_root, package, materialization_version=context["materialization_version"])
    return build_response(
        "derive_working_release_from_blueprint",
        headline="Working release derived from blueprint",
        summary_lines=[
            f"Blueprint: {blueprint_ref}",
            f"Target release: {saved['release']['release_id']}",
            f"Runtime locale: {saved['release']['default_runtime_locale']}",
        ],
        required_fields=["blueprint_ref"],
        references_existing_codes=saved["release"]["projection_ids"],
        blueprint_ref=blueprint_ref,
        derived_from_blueprint_ref=blueprint_ref,
        blueprint=blueprint,
        available_locales=list(saved["release"]["available_locales"]),
        default_authoring_locale=str(saved["release"]["default_authoring_locale"]),
        default_runtime_locale=str(saved["release"]["default_runtime_locale"]),
        projection_count=len(saved["release"]["projection_ids"]),
        generated_files=list(active_source_relative_files(saved)),
        provenance={"operation": "derive_working_release_from_blueprint", "blueprint_ref": blueprint_ref, "source": "immutable_default_blueprint"},
        compile_effect="The active working source package was replaced with immutable blueprint content; no separate compatibility files are materialized.",
        prompt_effect="The next review, compile, and export steps now read from the derived blueprint state.",
        corpus_effect="No corpus-visible change exists until compile, export, and activation run against the derived package.",
        validation_risks=[
            "The active working source package is replaced by the selected blueprint snapshot.",
            "Compile, export, and activation still need to run before downstream consumers see the new default.",
        ],
    )


def active_source_relative_files(package: dict[str, Any]) -> tuple[str, ...]:
    files = ["release.yaml", "master.core.yaml"]
    for locale in package["release"]["available_locales"]:
        files.append(f"master.text.{locale}.yaml")
        if locale in package.get("glossaries", {}):
            files.append(f"translation_glossary.{locale}.yaml")
    for projection_id in package["release"]["projection_ids"]:
        files.append(f"projections/{projection_id}.core.yaml")
        for locale in package["release"]["available_locales"]:
            files.append(f"projections/{projection_id}.text.{locale}.yaml")
    return tuple(files)


def _discover_blueprint_roots(project_root: Path) -> list[Path]:
    root = project_root / BLUEPRINT_ROOT_RELATIVE_PATH
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir()
        and (path / "blueprint.yaml").exists()
        and (path / "source_package" / "release.yaml").exists()
    )


def _require_blueprint_root(project_root: Path, blueprint_ref: str) -> Path:
    for root in _discover_blueprint_roots(project_root):
        if str(_load_blueprint_metadata(root).get("blueprint_ref") or "").strip() == blueprint_ref:
            return root
    raise ValueError(f"Blueprint nicht gefunden: {blueprint_ref}")


def _load_blueprint_metadata(root: Path) -> dict[str, Any]:
    payload = load_yaml_mapping(root / "blueprint.yaml", label="blueprint")
    if str(payload.get("blueprint_ref") or "").strip() != root.name:
        raise ValueError(f"blueprint.blueprint_ref stimmt nicht mit dem Ordnernamen ueberein: {root.name}")
    return payload


def _load_blueprint_package(root: Path) -> dict[str, object]:
    return validate_source_package(source_package_paths_for_root(root / "source_package"))


def _blueprint_descriptor(project_root: Path, root: Path) -> dict[str, Any]:
    metadata = _load_blueprint_metadata(root)
    release = _load_blueprint_package(root)["release"]
    return {
        "blueprint_ref": str(metadata["blueprint_ref"]),
        "label": required_text(metadata.get("label"), label="blueprint.label"),
        "description": required_text(metadata.get("description"), label="blueprint.description"),
        "kind": required_text(metadata.get("kind"), label="blueprint.kind"),
        "immutable": bool(metadata.get("immutable", True)),
        "primary_locale": required_text(metadata.get("primary_locale"), label="blueprint.primary_locale"),
        "release_id": str(release["release_id"]),
        "release_version": str(release["release_version"]),
        "available_locales": list(release["available_locales"]),
        "default_authoring_locale": str(release["default_authoring_locale"]),
        "default_runtime_locale": str(release["default_runtime_locale"]),
        "projection_count": len(release["projection_ids"]),
        "projection_ids": list(release["projection_ids"]),
        "source_path": str((root / "source_package").relative_to(project_root).as_posix()),
    }
