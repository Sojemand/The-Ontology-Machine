"""Repository helpers for persisted orchestrator UI and pipeline state."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, TypeVar

from ..models import PipelineState, RuntimeSettingsState, UiState
from ..models.provider_catalog import provider_ids_for_target
from .adapter import atomic_json_write, load_json_object

logger = logging.getLogger(__name__)

StateT = TypeVar("StateT", UiState, PipelineState)


def load_ui_state(path: Path) -> UiState:
    return _load_state(
        path,
        factory=UiState,
        read_error="Could not load UI state: %s",
        invalid_format="UI state has invalid format: %s",
        deserialize_error="UI state could not be deserialized: %s",
    )


def save_ui_state(path: Path, state: UiState) -> None:
    atomic_json_write(path, state.to_dict())


def load_pipeline_state(path: Path) -> PipelineState:
    return _load_state(
        path,
        factory=PipelineState,
        read_error="Could not load pipeline state: %s",
        invalid_format="Pipeline state has invalid format: %s",
        deserialize_error="Pipeline state could not be deserialized: %s",
    )


def save_pipeline_state(path: Path, state: PipelineState) -> None:
    state.updated_at = state.updated_at or ""
    atomic_json_write(path, state.to_dict())


def runtime_settings_path(state_dir: Path) -> Path:
    return Path(state_dir) / "runtime_settings.json"


def load_runtime_settings(state_dir: Path) -> RuntimeSettingsState:
    path = runtime_settings_path(state_dir)
    if not path.exists():
        return RuntimeSettingsState()
    try:
        data = _load_runtime_settings_payload(path)
        state = RuntimeSettingsState.from_dict(data)
        state.validate()
        return state
    except Exception as exc:
        raise ValueError(
            f"Runtime settings are invalid: {path}. Fix the file or delete it to regenerate defaults. {exc}"
        ) from exc


def save_runtime_settings(state_dir: Path, state: RuntimeSettingsState) -> None:
    state.validate()
    atomic_json_write(runtime_settings_path(state_dir), state.to_dict())


def _load_runtime_settings_payload(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"runtime_settings.json could not be read as JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("runtime_settings.json must contain a JSON object.")
    _validate_runtime_settings_payload(data)
    return data


def _validate_runtime_settings_payload(data: dict) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("runtime_settings.json has invalid schema_version.")
    _require_provider_section(data, "llm_shared_provider", target="llm_shared")
    _require_provider_section(data, "embeddings_provider", target="embeddings")
    _require_provider_section(data, "optimizer_ocr_provider", target="optimizer_ocr")
    _require_llm_section(data, "interpreter")
    _require_llm_section(data, "normalizer")
    _require_embedding_section(data, "corpus_builder_embeddings")
    _require_optimizer_ocr_section(data, "optimizer_ocr")


def _section(data: dict, key: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"runtime_settings.json section {key} must be an object.")
    return value


def _require_provider_section(data: dict, key: str, *, target: str) -> None:
    section = _section(data, key)
    _require_non_empty_text(section, "provider_id", section_name=key)
    _require_non_empty_text(section, "base_url", section_name=key)
    provider_id = section["provider_id"].strip().lower()
    if provider_id not in provider_ids_for_target(target):
        allowed = ", ".join(provider_ids_for_target(target))
        raise ValueError(f"runtime_settings.json section {key}.provider_id must be one of {allowed}.")


def _require_llm_section(data: dict, key: str) -> None:
    section = _section(data, key)
    _require_non_empty_text(section, "model", section_name=key)
    _require_positive_int(section, "max_output_tokens", section_name=key)


def _require_embedding_section(data: dict, key: str) -> None:
    section = _section(data, key)
    _require_non_empty_text(section, "model", section_name=key)


def _require_optimizer_ocr_section(data: dict, key: str) -> None:
    section = _section(data, key)
    _require_non_empty_text(section, "model", section_name=key)
    _require_positive_int(section, "max_output_tokens", section_name=key)
    _require_positive_int(section, "timeout_seconds", section_name=key)


def _require_non_empty_text(section: dict, field: str, *, section_name: str) -> None:
    if not isinstance(section.get(field), str) or not section.get(field, "").strip():
        raise ValueError(f"runtime_settings.json section {section_name}.{field} must be a non-empty string.")


def _require_positive_int(section: dict, field: str, *, section_name: str) -> None:
    value = section.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"runtime_settings.json section {section_name}.{field} must be a positive integer.")


def _load_state(
    path: Path,
    *,
    factory: Callable[[], StateT],
    read_error: str,
    invalid_format: str,
    deserialize_error: str,
) -> StateT:
    data = load_json_object(
        path,
        read_error=read_error,
        invalid_format=invalid_format,
    )
    if data is None:
        return factory()
    try:
        return factory.from_dict(data)
    except Exception:
        logger.warning(deserialize_error, path, exc_info=True)
        return factory()
