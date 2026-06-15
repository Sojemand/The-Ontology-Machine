from __future__ import annotations

from .tool_handler_deps import *
from .tool_handlers_artifact_rebuild import _corpus_optional_path_action


def inspect_active_corpus(arguments: dict[str, Any]) -> dict[str, Any]:
    return _corpus_optional_path_action("semantic_status", arguments)


def activate_corpus_context(arguments: dict[str, Any]) -> dict[str, Any]:
    corpus_db_path = _required_text(arguments, "corpus_db_path")
    corpus_output_folder = _corpus_output_folder(arguments, corpus_db_path)
    artifact_folder = _optional_text(arguments, "artifact_folder")
    input_folder = _optional_text(arguments, "input_folder")
    _validate_existing_context_target(corpus_db_path, corpus_output_folder)
    _validate_optional_artifact_root(corpus_output_folder, artifact_folder)
    _validate_optional_input_folder(input_folder, artifact_folder)
    corpus_builder = _invoke_product(
        "corpus_builder",
        {"action": "activate_corpus_context", "corpus_db_path": corpus_db_path},
    )
    orchestrator = _invoke_product(
        "orchestrator",
        _activate_orchestrator_payload(corpus_db_path, corpus_output_folder, artifact_folder, input_folder),
    )
    return {"status": "ok", "corpus_builder": corpus_builder, "orchestrator": orchestrator}


def create_empty_corpus_db(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(arguments) - {"corpus_db_path", "corpus_output_folder"})
    if unknown:
        raise ToolFailure(f"create_empty_corpus_db kennt diese Argumente nicht: {', '.join(unknown)}")
    corpus_db_path = _required_text(arguments, "corpus_db_path")
    corpus_output_folder = _corpus_output_folder(arguments, corpus_db_path)
    _validate_new_context_target(corpus_db_path, corpus_output_folder)
    created = _invoke_product(
        "corpus_builder",
        {
            "action": "create_empty_corpus_db",
            "corpus_db_path": corpus_db_path,
            "activate_context": False,
        },
    )
    return {"status": "ok", "created": created}


def _activate_orchestrator_payload(
    corpus_db_path: str,
    corpus_output_folder: str,
    artifact_folder: str,
    input_folder: str,
) -> dict[str, str]:
    payload = {
        "action": "activate_corpus_context",
        "corpus_db_path": corpus_db_path,
        "corpus_output_folder": corpus_output_folder,
    }
    if artifact_folder:
        payload["artifact_folder"] = artifact_folder
    if input_folder:
        payload["input_folder"] = input_folder
    return payload


__all__ = [name for name in globals() if not name.startswith("__")]
