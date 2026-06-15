from __future__ import annotations

from .tool_handler_deps import *


def activation_confirmation_for_preflight(
    preflight: dict[str, Any],
    *,
    artifact_path: Path,
    corpus_root: Path,
    database_stem: str,
    confirm_release_change: bool,
    activation_decision: str,
    requested_path: str,
) -> str:
    if not bool(preflight.get("requires_confirmation")):
        raise ToolFailure("activation_preflight_result.requires_confirmation muss true sein.")
    db_changes = preflight.get("db_changes") if isinstance(preflight.get("db_changes"), dict) else {}
    projection_drift = int(db_changes.get("projection_drift_documents") or 0)
    if projection_drift:
        raise ToolFailure(
            "Die neue Projection-Auswahl deckt bereits importierte Dokumente nicht sauber ab. "
            "Nutze read_revision_candidate_release -> inspect_release_revision_context -> activation_preflight -> "
            "classify_release_revision und waehle dann Projection erweitern, neue DB, oder Reset mit Re-Import."
        )
    if not confirm_release_change:
        raise ToolFailure(
            "Die DB enthaelt bereits Dokumente und die aktive Regelversion wuerde geaendert. "
            "Klassifiziere zuerst die Revision ueber read_revision_candidate_release -> "
            "inspect_release_revision_context -> activation_preflight -> classify_release_revision und setze "
            "confirm_release_change=true erst nach ausdruecklicher Zustimmung des Users."
        )
    template = preflight.get("confirmation_artifact_template")
    if not isinstance(template, dict):
        raise ToolFailure("Aktivierungs-Preflight lieferte keine confirmation_artifact_template.")
    confirmation_path = Path(
        requested_path or str(corpus_root / f"{database_stem}.release-change.confirmation.json")
    ).expanduser().resolve()
    if not _is_within(confirmation_path, artifact_path):
        raise ToolFailure("confirmation_artifact_path muss innerhalb von artifact_folder liegen.")
    payload = dict(template)
    payload["decision"] = activation_decision
    payload["confirmed_by_tool"] = "write_workspace_release_change_confirmation"
    payload["created_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_json_artifact(confirmation_path, payload)
    return str(confirmation_path)


def workspace_release_preflight_failure_message(message: str) -> str:
    lowered = message.casefold()
    if "master_taxonomy_release_id" in lowered or "master-linie" in lowered:
        return (
            "Die neue Regelversion gehoert zu einer anderen Taxonomie-Linie als die bereits importierten "
            "Dokumente. Das ist kein Backfill-Fall: Lege eine neue DB an oder nutze "
            "write_workspace_db_reset_confirmation -> reset_active_corpus_db nach ausdruecklichem Reset-Wunsch. "
            f"Preflight: {message}"
        )
    return (
        "Die Aktivierungspruefung hat die Regelversion fuer diese DB blockiert. "
        "Nutze read_revision_candidate_release -> inspect_release_revision_context -> activation_preflight -> "
        "classify_release_revision fuer die sichere Entscheidung. "
        f"Preflight: {message}"
    )


__all__ = [name for name in globals() if not name.startswith("__")]
