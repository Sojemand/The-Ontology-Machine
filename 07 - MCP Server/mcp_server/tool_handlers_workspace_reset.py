from __future__ import annotations

from .tool_handler_deps import *


def write_workspace_db_reset_confirmation(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(
        set(arguments)
        - {"artifact_folder", "database_name", "confirm_reset", "reset_reason", "confirmation_artifact_path"}
    )
    if unknown:
        raise ToolFailure(f"write_workspace_db_reset_confirmation kennt diese Argumente nicht: {', '.join(unknown)}")
    if _optional_bool(arguments, "confirm_reset", default=False) is not True:
        raise ToolFailure("confirm_reset=true ist erforderlich, weil vorhandene Dokumente geloescht werden.")
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    database_stem = _safe_database_stem(_required_text(arguments, "database_name"))
    reset_reason = _required_text(arguments, "reset_reason")
    corpus_root = artifact_path / "Corpus"
    corpus_db_path = corpus_root / f"{database_stem}.db"
    confirmation_path = Path(
        _optional_text(arguments, "confirmation_artifact_path")
        or str(corpus_root / f"{database_stem}.reset.confirmation.json")
    ).expanduser().resolve()
    if not _is_within(confirmation_path, artifact_path):
        raise ToolFailure("confirmation_artifact_path muss innerhalb von artifact_folder liegen.")
    _write_json_artifact(
        confirmation_path,
        {
            "artifact_version": "reset_active_corpus_db_confirmation_v1",
            "requested_action": "reset_active_corpus_db",
            "confirmed": True,
            "corpus_db_path": str(corpus_db_path),
            "reason": reset_reason,
            "created_by": "vision-pipeline-mcp",
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
    )
    return {
        "status": "ok",
        "artifact_folder": str(artifact_path),
        "corpus_output_folder": str(corpus_root),
        "corpus_db_path": str(corpus_db_path),
        "confirmation_artifact_path": str(confirmation_path),
        "confirmed": True,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
