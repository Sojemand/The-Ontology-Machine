from __future__ import annotations

from .tool_handler_deps import *


def classify_release_revision(
    *,
    db_state: dict[str, Any],
    candidate_summary: dict[str, Any],
    active_summary: dict[str, Any],
    preflight: dict[str, Any] | None,
    preflight_error: str | None,
) -> dict[str, Any]:
    document_count = int(db_state.get("document_count") or 0)
    db_has_documents = document_count > 0
    candidate_master = str(candidate_summary.get("master_taxonomy_release_id") or "").strip()
    active_master = str(active_summary.get("master_taxonomy_release_id") or "").strip()
    candidate_fingerprint = str(candidate_summary.get("fingerprint") or "").strip()
    active_fingerprint = str(active_summary.get("fingerprint") or "").strip()
    projection_drift_documents = _projection_drift_documents(preflight)
    if preflight_error:
        return _blocked_revision_plan(
            change_class=_blocked_change_class(preflight_error),
            db_has_documents=db_has_documents,
            preflight_error=preflight_error,
        )
    if not db_state.get("exists"):
        return _revision_plan(
            status="ready_for_new_database",
            change_class="new_database_activation",
            backfill_supported=False,
            requires_reset_or_new_db=False,
            safe_next_steps=[
                "prepare_pipeline_workspace_root",
                "create_empty_corpus_db",
                "export_working_release",
                "activation_preflight",
                "activate_release_on_existing_db",
                "activate_corpus_context",
                "verify_workspace_active_release",
            ],
            blocked_steps=["backfill_stale"],
            user_message=(
                "Die Regelversion ist vorbereitet. Es gibt noch keine DB an diesem Ziel; "
                "sie kann als neue Datenbank aktiviert und danach normal importiert werden."
            ),
        )
    if not db_has_documents:
        return _empty_database_plan()
    if active_master and candidate_master and active_master != candidate_master:
        return _master_changed_plan()
    if projection_drift_documents:
        return _projection_incompatible_plan()
    if active_fingerprint and candidate_fingerprint and active_fingerprint == candidate_fingerprint:
        return _same_release_plan()
    return _same_master_plan()


def _empty_database_plan() -> dict[str, Any]:
    return _revision_plan(
        status="ready_for_empty_database",
        change_class="empty_database_activation",
        backfill_supported=False,
        requires_reset_or_new_db=False,
        safe_next_steps=[
            "export_working_release",
            "activation_preflight",
            "activate_release_on_existing_db",
            "activate_corpus_context",
            "verify_workspace_active_release",
        ],
        blocked_steps=["backfill_stale"],
        user_message=(
            "Die bestehende DB enthaelt noch keine Dokumente. Die neue Regelversion kann "
            "aktiviert werden; ein Backfill ist nicht noetig."
        ),
    )


def _master_changed_plan() -> dict[str, Any]:
    return _revision_plan(
        status="needs_user_decision",
        change_class="master_taxonomy_changed",
        backfill_supported=False,
        requires_reset_or_new_db=True,
        safe_next_steps=["Regeln nur vorbereiten", "Neue DB mit diesen Regeln aufbauen", "Bestehende DB resetten und Quellen neu importieren"],
        blocked_steps=["activate_release_on_existing_db ohne Reset", "backfill_stale"],
        user_message=(
            "Diese Aenderung erweitert oder veraendert die erlaubten Archivbegriffe. "
            "Das ist eine neue Taxonomie-Linie. Die vorhandenen Dokumente wurden nicht "
            "mit diesen Begriffen normalisiert; ein Backfill reicht deshalb nicht. "
            "Waehle neue DB oder Reset mit Re-Import."
        ),
    )


def _projection_incompatible_plan() -> dict[str, Any]:
    return _revision_plan(
        status="needs_user_decision",
        change_class="projection_incompatible",
        backfill_supported=False,
        requires_reset_or_new_db=True,
        safe_next_steps=["Regeln nur vorbereiten", "Projection-Auswahl erweitern", "Bestehende DB resetten und Quellen neu importieren"],
        blocked_steps=["activate_and_backfill", "backfill_stale"],
        user_message=(
            "Die neue Profil-Auswahl deckt bereits importierte Dokumente nicht sauber ab. "
            "Erweitere die Projection-Auswahl oder baue die DB bewusst neu auf."
        ),
    )


def _same_release_plan() -> dict[str, Any]:
    return _revision_plan(
        status="no_change",
        change_class="same_release",
        backfill_supported=False,
        requires_reset_or_new_db=False,
        safe_next_steps=["keine Aktivierung noetig"],
        blocked_steps=["backfill_stale ohne stale documents"],
        user_message="Die aktive DB verwendet bereits diese Regelversion.",
    )


def _same_master_plan() -> dict[str, Any]:
    return _revision_plan(
        status="ready_for_same_master_activation",
        change_class="same_master_release_revision",
        backfill_supported=True,
        requires_reset_or_new_db=False,
        safe_next_steps=[
            "write_workspace_release_change_confirmation",
            "activate_release_on_existing_db mit confirmation_artifact_path",
            "backfill_stale",
        ],
        blocked_steps=["write_workspace_db_reset_confirmation -> reset_active_corpus_db ohne ausdruecklichen Reset-Wunsch"],
        user_message=(
            "Die Regelversion bleibt in derselben Taxonomie-Linie. Sie kann auf der bestehenden "
            "DB aktiviert werden; danach ist ein Backfill sinnvoll, weil nur vorhandene "
            "Semantik neu materialisiert wird."
        ),
    )


def _projection_drift_documents(preflight: dict[str, Any] | None) -> int:
    if not isinstance(preflight, dict):
        return 0
    db_changes = preflight.get("db_changes") if isinstance(preflight.get("db_changes"), dict) else {}
    return int(db_changes.get("projection_drift_documents") or 0)


def _blocked_change_class(message: str) -> str:
    lowered = message.casefold()
    if "master_taxonomy_release_id" in lowered or "master-linie" in lowered:
        return "master_taxonomy_changed"
    if "projection_id" in lowered:
        return "projection_incompatible"
    return "activation_preflight_blocked"


def _blocked_revision_plan(*, change_class: str, db_has_documents: bool, preflight_error: str) -> dict[str, Any]:
    requires_reset = db_has_documents and change_class in {"master_taxonomy_changed", "projection_incompatible"}
    safe_next_steps = ["Regeln nur vorbereiten"]
    if requires_reset:
        safe_next_steps.extend(["Neue DB mit diesen Regeln aufbauen", "Bestehende DB resetten und Quellen neu importieren"])
    return _revision_plan(
        status="needs_user_decision" if requires_reset else "blocked",
        change_class=change_class,
        backfill_supported=False,
        requires_reset_or_new_db=requires_reset,
        safe_next_steps=safe_next_steps,
        blocked_steps=["activate_release_on_existing_db", "backfill_stale"],
        user_message=(
            "Die Aktivierungspruefung blockiert diese Regelversion fuer die bestehende DB. "
            "Das ist kein Hintergrundfehler, sondern eine Schutzgrenze. "
            f"Originalmeldung: {preflight_error}"
        ),
    )


def _revision_plan(
    *,
    status: str,
    change_class: str,
    backfill_supported: bool,
    requires_reset_or_new_db: bool,
    safe_next_steps: list[str],
    blocked_steps: list[str],
    user_message: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "change_class": change_class,
        "backfill_supported": backfill_supported,
        "requires_reset_or_new_db": requires_reset_or_new_db,
        "safe_next_steps": safe_next_steps,
        "blocked_steps": blocked_steps,
        "user_message_de": user_message,
    }
__all__ = [name for name in globals() if not name.startswith("__")]
