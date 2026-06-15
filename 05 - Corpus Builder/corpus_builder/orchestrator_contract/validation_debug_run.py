"""Validation helpers for debug_run commands."""

from __future__ import annotations

from .types import DebugRunCommand


def parse_debug_options(payload: dict) -> bool:
    options = payload.get("options")
    if options is None:
        return False
    if not isinstance(options, dict):
        raise ValueError("options muss ein Objekt sein.")
    unknown = sorted(str(key) for key in options if str(key) != "persist_page_images_in_db")
    if unknown:
        raise ValueError(f"Unbekannte Felder in options: {', '.join(unknown)}")
    value = options.get("persist_page_images_in_db")
    if not isinstance(value, bool):
        raise ValueError("options.persist_page_images_in_db muss ein Bool sein.")
    return value


def validate_single_source(command: DebugRunCommand) -> None:
    if command.source_path is None:
        raise ValueError("source_path fehlt oder ist ungueltig.")
    if not command.source_path.exists():
        raise ValueError(f"Normalized JSON nicht gefunden: {command.source_path}")
    if not command.source_path.is_file():
        raise ValueError(f"source_path muss eine Datei sein: {command.source_path}")
    if not command.source_path.name.endswith(".structured.normalized.json"):
        raise ValueError("source_path muss auf *.structured.normalized.json zeigen.")


def validate_batch_root(command: DebugRunCommand) -> None:
    if command.input_root is None:
        raise ValueError("input_root fehlt oder ist ungueltig.")
    if not command.input_root.exists():
        raise ValueError(f"Artefaktordner nicht gefunden: {command.input_root}")
    if not command.input_root.is_dir():
        raise ValueError(f"input_root muss ein Verzeichnis sein: {command.input_root}")
