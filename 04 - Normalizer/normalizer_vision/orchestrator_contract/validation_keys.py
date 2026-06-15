"""Allowed payload keys for the normalizer orchestrator contract."""
from __future__ import annotations

NORMALIZE_DOCUMENT_KEYS = frozenset(
    {"action", "structured_path", "normalized_output_path", "request_output_path", "runtime_settings", "release"}
)
BUILD_PROJECTION_CATALOG_KEYS = frozenset({"action"})
BUILD_RUNTIME_SEMANTIC_ASSETS_KEYS = frozenset({"action", "release"})
PUBLISH_SEMANTIC_RELEASE_KEYS = frozenset(
    {"action", "release_id", "release_version", "projection_ids", "materialization_version", "target_locale", "output_path"}
)
LIST_DEFAULT_BLUEPRINTS_KEYS = frozenset({"action"})
EXPORT_DEFAULT_BLUEPRINT_RELEASE_KEYS = frozenset({"action", "blueprint_ref", "target_locale", "output_path"})
CREATE_ZERO_SHOT_WORKING_RELEASE_KEYS = frozenset(
    {"action", "blueprint_ref", "target_release_id", "target_release_version", "target_locale", "output_path"}
)
HEALTHCHECK_KEYS = frozenset({"action", "runtime_settings"})
DEBUG_RUN_KEYS = frozenset(
    {"action", "mode", "session_root", "output_root", "runtime_settings", "source_path", "input_root", "worker_count"}
)


def reject_legacy_overrides(payload: dict) -> None:
    if "overrides" in payload:
        raise ValueError("overrides wird nicht mehr akzeptiert. Verwende runtime_settings.")


def reject_legacy_output_dir(payload: dict) -> None:
    if "output_dir" in payload:
        raise ValueError("output_dir wird nicht mehr akzeptiert. Verwende normalized_output_path.")


def reject_runtime_settings(payload: dict, *, action: str) -> None:
    if "runtime_settings" in payload:
        raise ValueError(f"{action} akzeptiert keine runtime_settings.")


def reject_unknown_keys(payload: dict, allowed_keys: frozenset[str]) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed_keys)
    if unknown:
        raise ValueError(f"Unbekannte Felder: {', '.join(unknown)}")
