from __future__ import annotations

from pathlib import Path
from typing import Any

from ..state import atomic_json_write
from .release_activation_utils import dict_payload, int_value, short_id, text_value


def build_activation_confirmation_prompt(
    preflight: dict[str, Any],
    *,
    release_path: Path,
    corpus_db_path: Path,
) -> tuple[str, str]:
    db_changes = dict_payload(preflight.get("db_changes"))
    runtime_locale = dict_payload(preflight.get("runtime_locale"))
    current_locale = text_value(dict_payload(runtime_locale.get("current")).get("value"))
    next_locale = text_value(dict_payload(runtime_locale.get("next")).get("value"))
    current_snapshot_id = text_value(dict_payload(preflight.get("current_snapshot")).get("snapshot_id"))
    next_snapshot_id = text_value(dict_payload(preflight.get("next_snapshot")).get("snapshot_id"))
    stale_documents = int_value(db_changes.get("stale_documents_after_activation"))
    projection_drift = int_value(db_changes.get("projection_drift_documents"))
    title = _confirmation_title(
        projection_drift=projection_drift,
        stale_documents=stale_documents,
        current_locale=current_locale,
        next_locale=next_locale,
    )
    body_lines = [
        f"The release '{release_path.name}' would switch the active snapshot of this corpus.db.",
        "",
    ]
    body_lines.extend(
        _confirmation_impact_lines(
            projection_drift=projection_drift,
            stale_documents=stale_documents,
            current_locale=current_locale,
            next_locale=next_locale,
        )
    )
    body_lines.extend(
        [
            "",
            "Known activation outcome:",
            f"- The active snapshot changes from {short_id(current_snapshot_id) or 'none'} to {short_id(next_snapshot_id) or 'none'}.",
            "- The documents remain in the database.",
            (
                "- No automatic backfill starts here; stale documents must be updated later through backfill or rebuild."
                if stale_documents
                else "- No automatic backfill is needed."
            ),
            "",
            f"Target database: {corpus_db_path}",
            "",
            "Do you still want to activate the release?",
        ]
    )
    return title, "\n".join(body_lines)


def build_confirmation_payload(
    preflight: dict[str, Any],
    *,
    corpus_db_path: Path,
    decision: str,
) -> dict[str, Any]:
    template = dict_payload(preflight.get("confirmation_artifact_template"))
    if not template:
        raise ValueError("Activation preflight did not provide confirmation_artifact_template.")
    payload = dict(template)
    payload["corpus_db_path"] = str(corpus_db_path)
    payload["decision"] = str(decision or "").strip() or "activate_only"
    return payload


def write_confirmation_artifact(runtime_dir: Path, payload: dict[str, Any]) -> Path:
    artifact_path = runtime_dir / "release_activation.confirmation.json"
    atomic_json_write(artifact_path, payload)
    return artifact_path


def _confirmation_title(
    *,
    projection_drift: int,
    stale_documents: int,
    current_locale: str,
    next_locale: str,
) -> str:
    if projection_drift:
        return "Projection drift detected"
    if current_locale and next_locale and current_locale != next_locale:
        return "Runtime locale changes"
    if stale_documents:
        return "Release marks existing data as stale"
    return "Switch active release?"


def _confirmation_impact_lines(
    *,
    projection_drift: int,
    stale_documents: int,
    current_locale: str,
    next_locale: str,
) -> list[str]:
    if projection_drift:
        return [
            f"Detected impact: {projection_drift} active documents use projections that no longer match the new release.",
            f"Activation will mark {stale_documents} active documents as stale.",
        ]
    if current_locale and next_locale and current_locale != next_locale:
        return [
            f"Detected impact: the runtime locale changes from {current_locale} to {next_locale}.",
            (
                f"Activation will mark {stale_documents} active documents as stale."
                if stale_documents
                else "No already-active documents were detected that would become stale."
            ),
        ]
    if stale_documents:
        return [
            "Detected impact: the new release fingerprint no longer matches the currently materialized view of this DB.",
            f"Activation will mark {stale_documents} active documents as stale.",
        ]
    return ["No already-active documents were detected that would become stale."]
