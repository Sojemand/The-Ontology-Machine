from __future__ import annotations

from .tool_handler_activation_confirmation import activation_confirmation_for_preflight
from .tool_handler_deps import *
from .tool_handlers_semantic_release import read_active_semantic_release


def write_workspace_release_change_confirmation(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(
        set(arguments)
        - {
            "artifact_folder",
            "database_name",
            "activation_preflight_result",
            "activation_decision",
            "confirm_release_change",
            "confirmation_artifact_path",
        }
    )
    if unknown:
        raise ToolFailure(
            f"write_workspace_release_change_confirmation kennt diese Argumente nicht: {', '.join(unknown)}"
        )
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    database_stem = _safe_database_stem(_required_text(arguments, "database_name"))
    activation_decision = _required_text(arguments, "activation_decision")
    if activation_decision not in {"activate_only", "activate_and_backfill"}:
        raise ToolFailure("activation_decision muss 'activate_only' oder 'activate_and_backfill' sein.")
    preflight = _required_mapping(arguments, "activation_preflight_result")
    confirmation_path = activation_confirmation_for_preflight(
        preflight,
        artifact_path=artifact_path,
        corpus_root=artifact_path / "Corpus",
        database_stem=database_stem,
        confirm_release_change=_optional_bool(arguments, "confirm_release_change", default=False),
        activation_decision=activation_decision,
        requested_path=_optional_text(arguments, "confirmation_artifact_path"),
    )
    return {
        "status": "ok",
        "artifact_folder": str(artifact_path),
        "corpus_output_folder": str(artifact_path / "Corpus"),
        "corpus_db_path": str(artifact_path / "Corpus" / f"{database_stem}.db"),
        "confirmation_artifact_path": confirmation_path,
        "activation_decision": activation_decision,
        "confirmed": True,
    }


def verify_workspace_active_release(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(arguments) - {"artifact_folder", "database_name", "language", "projection_ids"})
    if unknown:
        raise ToolFailure(f"verify_workspace_active_release kennt diese Argumente nicht: {', '.join(unknown)}")
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    database_stem = _safe_database_stem(_required_text(arguments, "database_name"))
    language = _required_locale_argument(arguments, "language")
    projection_ids = _optional_string_list(arguments, "projection_ids")
    corpus_root = artifact_path / "Corpus"
    corpus_db_path = corpus_root / f"{database_stem}.db"
    _validate_existing_context_target(str(corpus_db_path), str(corpus_root))
    active_release = read_active_semantic_release({"corpus_db_path": str(corpus_db_path)})
    verification = _assert_semantic_release_selection(
        active_release,
        expected_language=language,
        expected_projection_ids=projection_ids,
        source_label="aktiver Workspace-DB Semantic Release",
    )
    return {
        "status": "ok",
        "artifact_folder": str(artifact_path),
        "corpus_output_folder": str(corpus_root),
        "corpus_db_path": str(corpus_db_path),
        "language": language,
        "projection_ids": projection_ids,
        "active_release": active_release,
        "verification": verification,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
