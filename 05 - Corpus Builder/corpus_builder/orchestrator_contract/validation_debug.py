"""Validation helpers for existing debug and loader contract commands."""
from __future__ import annotations

from .types import (
    ActivateCorpusContextCommand,
    ActivationPreflightCommand,
    ActivateSemanticReleaseCommand,
    CreateAndActivateNewCorpusDbCommand,
    CreateEmptyCorpusDbCommand,
    DebugRunCommand,
    GenerateEmbeddingsCommand,
    HealthcheckCommand,
    LoadDocumentCommand,
    ScanDebugInputCommand,
)
from .validation_common import (
    missing,
    optional_path,
    optional_string,
    parse_bool,
    parse_runtime_settings,
    reject_unknown_keys,
    required_path,
    required_string,
    validate_output_root,
    validate_session_root,
)
from .validation_debug_run import parse_debug_options, validate_batch_root, validate_single_source

_LOAD_DOCUMENT_KEYS = frozenset({
    "action",
    "corpus_db_path",
    "normalized_path",
    "structured_path",
    "validation_path",
    "raw_path",
    "persist_page_images_in_db",
    "page_images_dir",
})
_ACTIVATE_RELEASE_KEYS = frozenset({
    "action",
    "confirmation_artifact_path",
    "corpus_db_path",
    "release_path",
    "write_global_mirrors",
})
_ACTIVATE_CORPUS_CONTEXT_KEYS = frozenset({"action", "corpus_db_path"})
_CREATE_EMPTY_CORPUS_DB_KEYS = frozenset({"action", "activate_context", "corpus_db_path"})
_CREATE_AND_ACTIVATE_NEW_CORPUS_DB_KEYS = frozenset({"action", "confirmation_artifact_path", "release_path"})
_ACTIVATION_PREFLIGHT_KEYS = frozenset({"action", "corpus_db_path", "release_path"})
_GENERATE_EMBEDDINGS_KEYS = frozenset({"action", "corpus_db_path", "runtime_model", "runtime_settings"})
_HEALTHCHECK_KEYS = frozenset({"action", "corpus_db_path", "runtime_settings", "scope"})
_SCAN_DEBUG_INPUT_KEYS = frozenset({"action", "input_root", "mode", "session_root"})
_DEBUG_RUN_KEYS = frozenset({"action", "input_root", "mode", "options", "output_root", "session_root", "source_path"})


def parse_load_document_command(payload: dict) -> LoadDocumentCommand:
    reject_unknown_keys(payload, _LOAD_DOCUMENT_KEYS)
    return LoadDocumentCommand(
        corpus_db_path=required_string(payload, "corpus_db_path") or missing("corpus_db_path"),
        normalized_path=required_string(payload, "normalized_path") or missing("normalized_path"),
        structured_path=required_string(payload, "structured_path") or missing("structured_path"),
        validation_path=required_string(payload, "validation_path") or missing("validation_path"),
        raw_path=optional_string(payload, "raw_path"),
        persist_page_images_in_db=_optional_bool(payload, "persist_page_images_in_db"),
        page_images_dir=optional_string(payload, "page_images_dir"),
    )


def _optional_bool(payload: dict, key: str) -> bool | None:
    if key not in payload:
        return None
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} muss true oder false sein.")
    return value


def parse_activate_semantic_release_command(payload: dict) -> ActivateSemanticReleaseCommand:
    reject_unknown_keys(payload, _ACTIVATE_RELEASE_KEYS)
    return ActivateSemanticReleaseCommand(
        release_path=required_string(payload, "release_path") or missing("release_path"),
        corpus_db_path=optional_string(payload, "corpus_db_path"),
        confirmation_artifact_path=optional_string(payload, "confirmation_artifact_path"),
        write_global_mirrors=parse_bool(payload, "write_global_mirrors", default=True),
    )


def parse_activate_corpus_context_command(payload: dict) -> ActivateCorpusContextCommand:
    reject_unknown_keys(payload, _ACTIVATE_CORPUS_CONTEXT_KEYS)
    return ActivateCorpusContextCommand(
        corpus_db_path=required_string(payload, "corpus_db_path") or missing("corpus_db_path"),
    )


def parse_create_empty_corpus_db_command(payload: dict) -> CreateEmptyCorpusDbCommand:
    reject_unknown_keys(payload, _CREATE_EMPTY_CORPUS_DB_KEYS)
    return CreateEmptyCorpusDbCommand(
        corpus_db_path=required_string(payload, "corpus_db_path") or missing("corpus_db_path"),
        activate_context=parse_bool(payload, "activate_context", default=False),
    )


def parse_create_and_activate_new_corpus_db_command(payload: dict) -> CreateAndActivateNewCorpusDbCommand:
    reject_unknown_keys(payload, _CREATE_AND_ACTIVATE_NEW_CORPUS_DB_KEYS)
    return CreateAndActivateNewCorpusDbCommand(
        release_path=required_string(payload, "release_path") or missing("release_path"),
        confirmation_artifact_path=required_string(payload, "confirmation_artifact_path") or missing("confirmation_artifact_path"),
    )


def parse_activation_preflight_command(payload: dict) -> ActivationPreflightCommand:
    reject_unknown_keys(payload, _ACTIVATION_PREFLIGHT_KEYS)
    return ActivationPreflightCommand(
        release_path=required_string(payload, "release_path") or missing("release_path"),
        corpus_db_path=optional_string(payload, "corpus_db_path"),
    )


def parse_generate_embeddings_command(payload: dict) -> GenerateEmbeddingsCommand:
    reject_unknown_keys(payload, _GENERATE_EMBEDDINGS_KEYS)
    return GenerateEmbeddingsCommand(
        corpus_db_path=required_string(payload, "corpus_db_path") or missing("corpus_db_path"),
        runtime_settings=_generate_runtime_settings(payload),
    )


def parse_healthcheck_command(payload: dict) -> HealthcheckCommand:
    reject_unknown_keys(payload, _HEALTHCHECK_KEYS)
    return HealthcheckCommand(
        runtime_settings=parse_runtime_settings(payload),
        scope=optional_string(payload, "scope"),
        corpus_db_path=optional_string(payload, "corpus_db_path"),
    )


def parse_scan_debug_input_command(payload: dict) -> ScanDebugInputCommand:
    reject_unknown_keys(payload, _SCAN_DEBUG_INPUT_KEYS)
    mode = required_string(payload, "mode")
    if mode != "scan":
        raise ValueError("mode muss scan sein.")
    command = ScanDebugInputCommand(mode=mode, session_root=required_path(payload, "session_root"), input_root=required_path(payload, "input_root"))
    validate_session_root(command.session_root)
    if not command.input_root.exists():
        raise ValueError(f"Artefaktordner nicht gefunden: {command.input_root}")
    if not command.input_root.is_dir():
        raise ValueError(f"input_root muss ein Verzeichnis sein: {command.input_root}")
    return command


def parse_debug_run_command(payload: dict) -> DebugRunCommand:
    reject_unknown_keys(payload, _DEBUG_RUN_KEYS)
    mode = required_string(payload, "mode")
    if mode not in {"single", "batch"}:
        raise ValueError("mode muss single oder batch sein.")
    command = DebugRunCommand(
        mode=mode,
        session_root=required_path(payload, "session_root"),
        output_root=required_path(payload, "output_root"),
        input_root=optional_path(payload.get("input_root")),
        source_path=optional_path(payload.get("source_path")),
        persist_page_images_in_db=parse_debug_options(payload),
    )
    validate_session_root(command.session_root)
    validate_output_root(command.output_root)
    if command.mode == "single":
        validate_single_source(command)
    else:
        validate_batch_root(command)
    return command


def _generate_runtime_settings(payload: dict):
    if "runtime_settings" in payload:
        return parse_runtime_settings(payload)
    model = required_string(payload, "runtime_model")
    if model is None:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    return parse_runtime_settings({"runtime_settings": {"model": model}})
