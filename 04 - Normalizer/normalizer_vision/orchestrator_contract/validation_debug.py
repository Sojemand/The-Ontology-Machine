"""Debug-run command parsing for the normalizer subprocess contract."""
from __future__ import annotations

from . import value_parsing
from .types import DebugRunCommand
from .validation_keys import DEBUG_RUN_KEYS, reject_legacy_overrides, reject_unknown_keys
from .validation_paths import require_structured_json_path, validate_session_paths
from .validation_runtime import parse_runtime_settings

DEBUG_RUN_MODES = ("single", "batch")


def parse_debug_run_command(payload: dict) -> DebugRunCommand:
    reject_legacy_overrides(payload)
    reject_unknown_keys(payload, DEBUG_RUN_KEYS)
    mode = value_parsing.required_string(payload, "mode")
    if mode not in DEBUG_RUN_MODES:
        raise ValueError(f"mode muss {' oder '.join(DEBUG_RUN_MODES)} sein.")
    command = DebugRunCommand(
        mode=mode,  # type: ignore[arg-type]
        session_root=value_parsing.required_path(payload, "session_root"),
        output_root=value_parsing.required_path(payload, "output_root"),
        runtime_settings=parse_runtime_settings(payload),
        source_path=value_parsing.optional_path(payload.get("source_path")),
        input_root=value_parsing.optional_path(payload.get("input_root")),
        worker_count=value_parsing.optional_worker_count(payload.get("worker_count")),
    )
    validate_session_paths(command)
    if command.mode == "single":
        _validate_single_source(command)
    else:
        _validate_batch_input(command)
    return command


def _validate_single_source(command: DebugRunCommand) -> None:
    if command.source_path is None:
        raise ValueError("source_path fehlt oder ist ungueltig.")
    require_structured_json_path(command.source_path, label="source_path")
    if not command.source_path.exists():
        raise ValueError(f"Structured JSON nicht gefunden: {command.source_path}")
    if not command.source_path.is_file():
        raise ValueError(f"Structured JSON muss eine Datei sein: {command.source_path}")


def _validate_batch_input(command: DebugRunCommand) -> None:
    if command.input_root is None:
        raise ValueError("input_root fehlt oder ist ungueltig.")
    if not command.input_root.exists():
        raise ValueError(f"Structured-Ordner nicht gefunden: {command.input_root}")
    if not command.input_root.is_dir():
        raise ValueError(f"Structured-Eingabe muss ein Ordner sein: {command.input_root}")
