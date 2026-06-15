"""Confirmation-artifact parsing for new Corpus DB provisioning."""

from __future__ import annotations

import json
from pathlib import Path

_CONFIRMATION_VERSION = "new_corpus_db_confirmation_v1"


def load_new_corpus_db_confirmation(
    artifact_path: str | Path,
    *,
    expected_action: str,
) -> dict[str, str | None]:
    path = Path(artifact_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Confirmation-Artefakt fehlt: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Confirmation-Artefakt muss ein JSON-Objekt sein.")
    version = str(payload.get("artifact_version") or "").strip()
    if version != _CONFIRMATION_VERSION:
        raise ValueError(f"Ungueltige Confirmation-Version: {version or '<leer>'}")
    action = str(payload.get("requested_action") or "").strip()
    if action != expected_action:
        raise ValueError(f"Confirmation-Artefakt passt nicht zu {expected_action}.")
    if payload.get("confirmed") is not True:
        raise ValueError("Neue Corpus-DB erfordert bestaetigte Confirmation.")
    database_label = str(payload.get("database_label") or "").strip()
    taxonomy_locale = str(payload.get("taxonomy_locale") or "").strip().lower()
    if not database_label:
        raise ValueError("Confirmation-Artefakt enthaelt keine Datenbank-Bezeichnung.")
    if not taxonomy_locale:
        raise ValueError("Confirmation-Artefakt enthaelt keine Taxonomie-Sprache.")
    corpus_root = str(payload.get("corpus_root") or "").strip()
    if not corpus_root:
        raise ValueError("Confirmation-Artefakt enthaelt keinen corpus_root.")
    return {
        "database_label": database_label,
        "taxonomy_locale": taxonomy_locale,
        "corpus_root": corpus_root,
    }


__all__ = ["load_new_corpus_db_confirmation"]
