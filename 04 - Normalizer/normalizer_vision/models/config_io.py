"""Config file loading, saving, and path policy."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .coercion import build_project_config_payload
from .config_types import NormalizerProjectConfig
from .serialization import atomic_text_write
from .types import (
    CONFIG_BOOL_FIELDS,
    CONFIG_INT_FIELDS,
    DEFAULT_CONFIG_RELATIVE_PATH,
    LEGACY_ASSET_KEYS,
    REMOVED_INTERNAL_PATH_FIELDS,
    REMOVED_RUNTIME_CONFIG_FIELDS,
)
from ..projection_routing_settings import validate_routing_settings

SUPPORTED_PROVIDER_FAMILIES = {
    "openai",
    "openai_compat",
    "openai-compatible",
    "lmstudio",
    "ollama",
    "anthropic",
    "google",
    "gemini",
    "xai",
    "openrouter",
    "groq",
    "together",
    "fireworks",
    "mistral",
    "deepseek",
    "sambanova",
    "cerebras",
    "mammouth",
}


def load_config(project_root: Path, config_path: Path | None = None) -> NormalizerProjectConfig:
    cfg_path = _resolve_local_path(project_root, config_path, label="config_path")
    data = _load_yaml_mapping(cfg_path)
    provider = str(data.get("provider", "openai")).strip().lower() or "openai"
    if provider not in SUPPORTED_PROVIDER_FAMILIES:
        raise ValueError("provider muss einer orchestrator-kompatiblen Providerfamilie entsprechen")
    _validate_legacy_asset_paths(data)
    _validate_removed_auth_fields(data)
    _validate_removed_runtime_fields(data)
    _validate_unknown_config_fields(data)
    validate_routing_settings(data.get("projection_routing", {}))
    return NormalizerProjectConfig(**build_project_config_payload(data))


def save_config(project_root: Path, config: NormalizerProjectConfig) -> None:
    config_path = project_root / DEFAULT_CONFIG_RELATIVE_PATH
    payload = config.to_dict()
    current = _load_yaml_mapping(config_path)
    provider = str(current.get("provider") or "").strip()
    if provider:
        payload["provider"] = provider
    payload["projection_routing"] = validate_routing_settings(current.get("projection_routing", {}))
    atomic_text_write(config_path, yaml.safe_dump(payload, sort_keys=False))


def _resolve_local_path(project_root: Path, value: str | Path | None, *, label: str) -> Path:
    candidate = Path(value) if value is not None else DEFAULT_CONFIG_RELATIVE_PATH
    if not candidate.is_absolute() and ".." in candidate.parts:
        raise ValueError(f"{label} darf keine Parent-Segmente enthalten: {candidate}")
    resolved = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} muss innerhalb des Moduls liegen: {candidate}") from exc
    return resolved


def _load_yaml_mapping(cfg_path: Path) -> dict[str, Any]:
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ValueError(f"Config konnte nicht geladen werden: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("config.yaml muss ein Objekt enthalten.")
    return data


def _validate_legacy_asset_paths(data: dict[str, Any]) -> None:
    removed = sorted(key for key in REMOVED_INTERNAL_PATH_FIELDS if key in data)
    if removed:
        raise ValueError("Diese internen Pfadfelder werden nicht mehr unterstuetzt: " + ", ".join(removed))
    for key, expected in LEGACY_ASSET_KEYS.items():
        raw_value = data.get(key)
        if raw_value is None or raw_value == "":
            continue
        candidate = Path(str(raw_value).replace("\\", "/"))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"{key} darf kein externer Pfad sein: {raw_value}")
        if candidate.as_posix() != expected:
            raise ValueError(f"{key} ist nicht mehr frei konfigurierbar und muss intern bleiben.")


def _validate_removed_auth_fields(data: dict[str, Any]) -> None:
    for key in ("api_key", "api_base_url"):
        if key in data:
            raise ValueError(f"{key} wird nicht mehr modul-lokal konfiguriert.")


def _validate_removed_runtime_fields(data: dict[str, Any]) -> None:
    forbidden = sorted(key for key in REMOVED_RUNTIME_CONFIG_FIELDS if key in data)
    if forbidden:
        raise ValueError("config.yaml darf keine lokale Modell-Ownership mehr enthalten: " + ", ".join(forbidden))


def _validate_unknown_config_fields(data: dict[str, Any]) -> None:
    allowed = (
        set(CONFIG_INT_FIELDS)
        | set(CONFIG_BOOL_FIELDS)
        | {"provider", "projection_hint_mode", "projection_routing", "taxonomy_profile_id"}
        | set(LEGACY_ASSET_KEYS)
    )
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError("config.yaml enthaelt unbekannte Felder: " + ", ".join(unknown))
