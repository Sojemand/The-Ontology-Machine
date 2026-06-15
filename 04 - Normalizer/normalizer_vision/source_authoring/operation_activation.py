"""Corpus activation source-authoring operations."""
from __future__ import annotations

import json
from typing import Any

from ..taxonomy_sources import policy as source_policy
from . import corpus_proxy
from .operation_build_chain import validate_release_package
from .operation_common import ensure_compiled, locale_source, optional_locale, publish_release, required_bundle_path, required_text
from .response import build_response


def activate_semantic_release(project_root, payload: dict[str, Any]) -> dict[str, object]:
    output_path = required_bundle_path(payload.get("release_path"), label="release_path")
    corpus_db_path = required_text(payload.get("corpus_db_path"), label="corpus_db_path")
    target_locale = optional_locale(payload.get("target_locale"), label="target_locale")
    _validate_and_compile(project_root, target_locale=target_locale)
    release = publish_release(project_root, output_path, target_locale=target_locale)
    activation = corpus_proxy.activate_release(project_root, release_path=str(output_path), corpus_db_path=corpus_db_path)
    if str(activation.get("status") or "").casefold() not in {"ok", "applied"}:
        raise ValueError(str(activation.get("reason") or "Corpus-Builder-Aktivierung fehlgeschlagen."))
    runtime_locale = str(release.get("runtime_locale") or "").strip()
    return build_response(
        "activate_semantic_release",
        headline="Semantic release exported and activated",
        summary_lines=[
            f"Release: {release['release_id']}",
            f"Version: {release['release_version']}",
            f"Runtime locale: {runtime_locale} ({locale_source(target_locale)})",
            f"Activation status: {activation.get('status')}",
        ],
        required_fields=["release_path", "corpus_db_path"],
        references_existing_codes=release["projection_ids"],
        output_path=str(output_path),
        runtime_locale=runtime_locale,
        locale_resolution={"runtime_locale": runtime_locale, "source": locale_source(target_locale)},
        artifacts=[{"label": "Release Bundle", "value": str(output_path)}, {"label": "Corpus DB", "value": corpus_db_path}],
        compile_effect="Source files were validated, compiled, and exported as a JSON release bundle before activation.",
        prompt_effect="No prompt effect beyond the exported release that now reflects saved source changes.",
        corpus_effect="The exported JSON release bundle was activated through the Corpus Builder contract.",
    )


def create_and_activate_new_corpus_db(project_root, payload: dict[str, Any]) -> dict[str, object]:
    output_path = required_bundle_path(payload.get("release_path"), label="release_path")
    confirmation_path = required_text(payload.get("confirmation_artifact_path"), label="confirmation_artifact_path")
    confirmation = _read_new_corpus_db_confirmation(confirmation_path)
    taxonomy_locale = source_policy.require_locale(confirmation["taxonomy_locale"], label="taxonomy_locale")
    _validate_and_compile(project_root, target_locale=taxonomy_locale)
    release = publish_release(project_root, output_path, target_locale=taxonomy_locale)
    activation = corpus_proxy.create_and_activate_new_corpus_db(
        project_root,
        release_path=str(output_path),
        confirmation_artifact_path=confirmation_path,
    )
    if str(activation.get("status") or "").casefold() not in {"ok", "applied"}:
        raise ValueError(str(activation.get("reason") or "Corpus-Builder-Neuerstellung fehlgeschlagen."))
    runtime_locale = str(release.get("runtime_locale") or "").strip()
    corpus_db_path = str(activation.get("corpus_db_path") or "").strip()
    return build_response(
        "create_and_activate_new_corpus_db",
        headline="New corpus DB created and semantic release activated",
        summary_lines=[
            f"Release: {release['release_id']}",
            f"Version: {release['release_version']}",
            f"Runtime locale: {runtime_locale} (explicit_target_locale)",
            f"Activation status: {activation.get('status')}",
        ],
        required_fields=["release_path", "confirmation_artifact_path"],
        references_existing_codes=release["projection_ids"],
        output_path=str(output_path),
        runtime_locale=runtime_locale,
        locale_resolution={"runtime_locale": runtime_locale, "source": "explicit_target_locale"},
        artifacts=[{"label": "Release Bundle", "value": str(output_path)}, {"label": "Corpus DB", "value": corpus_db_path}],
        compile_effect="Source files were validated, compiled, and exported as a JSON release bundle before a fresh corpus DB was provisioned.",
        prompt_effect="No prompt effect beyond the exported release that now reflects saved source changes.",
        corpus_effect="A new corpus DB was created, activated, and set as the default target without mutating the previous database.",
        corpus_db_path=corpus_db_path,
        previous_default_corpus_db_path=activation.get("previous_default_corpus_db_path"),
        taxonomy_locale=taxonomy_locale,
        database_label=confirmation["database_label"],
    )


def _validate_and_compile(project_root, *, target_locale: str | None) -> None:
    from . import operations as operations_facade

    validator = getattr(operations_facade, "validate_release_package", validate_release_package)
    if target_locale is None:
        validator(project_root)
    else:
        validator(project_root, {"target_locale": target_locale})
    if ensure_compiled(project_root, target_locale=target_locale) is None:
        raise ValueError("Aktives Source-Paket fehlt.")


def _read_new_corpus_db_confirmation(value: str) -> dict[str, str]:
    from pathlib import Path

    path = Path(value).expanduser()
    if not path.exists():
        raise ValueError(f"confirmation_artifact_path fehlt: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("confirmation_artifact_path muss ein JSON-Objekt sein.")
    if str(payload.get("artifact_version") or "").strip() != "new_corpus_db_confirmation_v1":
        raise ValueError("confirmation_artifact_path hat eine ungueltige Version.")
    if payload.get("confirmed") is not True:
        raise ValueError("Neue Corpus-DB erfordert bestaetigte Confirmation.")
    return {
        "database_label": required_text(payload.get("database_label"), label="database_label"),
        "taxonomy_locale": required_text(payload.get("taxonomy_locale"), label="taxonomy_locale"),
    }
