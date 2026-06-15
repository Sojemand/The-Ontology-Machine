from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import ReleaseActivationStageResult
from .release_activation_utils import dict_payload, int_value, short_id, text_value


def build_activation_blocked_message(
    reason: str,
    *,
    release_path: Path,
    corpus_db_path: Path,
) -> str:
    detail = str(reason or "").strip() or "Semantic Release cannot be activated."
    normalized = detail.casefold()
    if "ohne projection_id" in normalized:
        return (
            f"The release '{release_path.name}' cannot be activated for {corpus_db_path.name}. "
            "The database contains active documents without projection_id. "
            "These data cannot be assigned to a safe release snapshot; override is blocked here. "
            f"Details: {detail}"
        )
    if "master-taxonomie-linie" in normalized or "master_taxonomy_release_id" in normalized or "anderen master" in normalized:
        return (
            f"The release '{release_path.name}' cannot be activated for {corpus_db_path.name}. "
            "The active data state belongs to a different master taxonomy line. "
            "Switching would make the existing DB semantically inconsistent, so override is not allowed here. "
            f"Details: {detail}"
        )
    return (
        f"The release '{release_path.name}' cannot be activated for {corpus_db_path.name}. "
        f"Details: {detail}"
    )


def build_selected_release_needs_activation_message(
    preflight: dict[str, Any],
    *,
    release_path: Path,
    corpus_db_path: Path,
) -> str:
    if bool(preflight.get("initialization_required")):
        return (
            f"The selected release '{release_path.name}' is not active for {corpus_db_path.name} yet. "
            "Activate it first; normal runs no longer switch releases silently in the background."
        )
    if not bool(preflight.get("requires_confirmation")):
        return (
            f"The selected release '{release_path.name}' is not active for {corpus_db_path.name} yet. "
            "Activate it first."
        )
    stale_documents = int_value(dict_payload(preflight.get("db_changes")).get("stale_documents_after_activation"))
    projection_drift = int_value(dict_payload(preflight.get("db_changes")).get("projection_drift_documents"))
    if projection_drift:
        return (
            f"The selected release '{release_path.name}' would switch the active snapshot of {corpus_db_path.name} "
            f"and mark {stale_documents} active documents as stale because their stored projections no longer "
            "match the new release. Confirm the switch deliberately through Activate."
        )
    if stale_documents:
        return (
            f"The selected release '{release_path.name}' would switch the active snapshot of {corpus_db_path.name} "
            f"and mark {stale_documents} active documents as stale. Confirm the switch deliberately through Activate."
        )
    return (
        f"The selected release '{release_path.name}' would switch the active snapshot of {corpus_db_path.name}. "
        "Confirm the switch deliberately through Activate."
    )


def annotated_release_failure(detail: str, *, release_path: Path, corpus_db_path: Path) -> str:
    message = str(detail).strip() or "Semantic Release could not be activated."
    if "release_path=" not in message:
        message = f"{message} [release_path={release_path}]"
    if "corpus_db_path=" in message:
        return message
    return f"{message} [corpus_db_path={corpus_db_path}]"


def activation_success_detail(*, result: ReleaseActivationStageResult, release_path: Path) -> str:
    parts = [
        "Release active",
        release_path.name,
        result.release_id.strip(),
        result.release_version.strip(),
        short_id(result.active_snapshot_id),
    ]
    detail = " | ".join(part for part in parts if part)
    if result.backfill_started:
        return f"{detail} | Backfill: {result.backfill_processed_count}"
    if result.stale_documents:
        return f"{detail} | stale documents: {result.stale_documents}"
    return detail
