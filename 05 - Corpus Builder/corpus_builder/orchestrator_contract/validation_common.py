"""Shared payload-validation helpers for contract commands."""
from __future__ import annotations

from pathlib import Path

from ..models.types import EmbeddingRuntimeSettings


def required_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def optional_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} muss ein String sein.")
    text = value.strip()
    return text or None


def required_path(payload: dict, key: str) -> Path:
    value = required_string(payload, key)
    if value is None:
        raise ValueError(f"{key} fehlt oder ist ungueltig.")
    return Path(value)


def optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Pfadoptionen muessen Strings sein.")
    text = value.strip()
    return Path(text) if text else None


def reject_unknown_keys(payload: dict, allowed_keys: frozenset[str]) -> None:
    unknown = sorted(str(key) for key in payload if str(key) not in allowed_keys)
    if unknown:
        raise ValueError(f"Unbekannte Felder: {', '.join(unknown)}")


def parse_runtime_settings(payload: dict) -> EmbeddingRuntimeSettings:
    runtime_settings = payload.get("runtime_settings")
    if not isinstance(runtime_settings, dict):
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    unknown = sorted(str(key) for key in runtime_settings if str(key) != "model")
    if unknown:
        raise ValueError(f"Unbekannte Felder in runtime_settings: {', '.join(unknown)}")
    model = required_string(runtime_settings, "model")
    if model is None:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    return EmbeddingRuntimeSettings(model=model)


def parse_optional_int(payload: dict, key: str) -> int | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} muss eine Ganzzahl sein.")
    return value


def parse_bool(payload: dict, key: str, *, default: bool = False) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} muss true oder false sein.")
    return value


def parse_string_list(payload: dict, key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if value is None or value == "":
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{key} muss eine Liste nicht-leerer Strings sein.")
    return tuple(item.strip() for item in value)


def missing(key: str) -> str:
    raise ValueError(f"{key} fehlt oder ist ungueltig.")


def validate_session_root(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"session_root muss ein Verzeichnis sein: {path}")


def validate_output_root(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"output_root muss ein Verzeichnis sein: {path}")
