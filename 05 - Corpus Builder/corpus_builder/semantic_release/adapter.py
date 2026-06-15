"""Boundary helpers for semantic release file I/O."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..context import ModuleContext
from ..models.serialization import atomic_bytes_write, atomic_json_write
from ..models.types import CorpusConfig
from .types import ReleaseAnalysis, ReleasePayload
from .validation import validate_release_payload

CANONICAL_DEFAULT_MASTER_TAXONOMY_ID = "normalizer_taxonomy.master"
CANONICAL_DEFAULT_RELEASE_ID = "semantic_release.default"
DEFAULT_RELEASE_FILE_NAME = "semantic_release.default.json"


def load_release_from_path(path: Path, *, stage: str = "release") -> ReleasePayload:
    _require_release_bundle_path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _release_error(exc, path, stage=stage) from exc
    if not isinstance(payload, dict):
        raise _release_error("Semantic Release muss ein JSON-Objekt sein.", path, stage=stage)
    fingerprint = _release_fingerprint(payload)
    try:
        return validate_release_payload(payload)
    except ValueError as exc:
        raise _release_error(exc, path, stage=stage, fingerprint=fingerprint) from exc


def load_published_release(context: ModuleContext, config: CorpusConfig) -> tuple[ReleasePayload, Path]:
    published_path = context.resolve_path(config.semantic.published_release_path)
    if not published_path.exists():
        raise ValueError(f"Veroeffentlichter Semantic Release fehlt: {published_path}")
    return load_release_from_path(published_path, stage="published_release"), published_path


def stage_published_release(
    context: ModuleContext,
    config: CorpusConfig,
    source_path: str | Path,
) -> tuple[ReleasePayload, Path, Path]:
    resolved_source = context.resolve_path(source_path)
    if not resolved_source.exists():
        raise ValueError(f"Semantic Release nicht gefunden: {resolved_source}")
    owner_local_source = _owner_local_source_path(context, resolved_source)
    release = load_release_from_path(owner_local_source, stage="source_release")
    target_path = context.resolve_path(config.semantic.published_release_path)
    assert_default_release_write_allowed(target_path, release)
    atomic_json_write(target_path, release)
    return release, resolved_source, target_path


def assert_default_release_write_allowed(target_path: Path, release: Mapping[str, Any]) -> None:
    if target_path.name.casefold() != DEFAULT_RELEASE_FILE_NAME:
        return
    release_id = str(release.get("release_id") or "").strip()
    master_taxonomy_id = str(release.get("master_taxonomy_id") or "").strip()
    if release_id == CANONICAL_DEFAULT_RELEASE_ID and master_taxonomy_id == CANONICAL_DEFAULT_MASTER_TAXONOMY_ID:
        return
    raise ValueError(
        "Canonical Default Semantic Release is immutable: "
        f"{DEFAULT_RELEASE_FILE_NAME} only accepts {CANONICAL_DEFAULT_RELEASE_ID} "
        f"on {CANONICAL_DEFAULT_MASTER_TAXONOMY_ID}, got {release_id or '<missing>'} "
        f"on {master_taxonomy_id or '<missing>'}."
    )


def load_active_release(context: ModuleContext, config: CorpusConfig) -> tuple[ReleasePayload, Path]:
    active_path = context.resolve_path(config.semantic.active_release_path)
    if not active_path.exists():
        raise ValueError(
            "Kein aktiver Semantic Release vorhanden. Wende zuerst den veroeffentlichten Release an."
        )
    return load_release_from_path(active_path, stage="active_release"), active_path


def write_release_analysis(context: ModuleContext, config: CorpusConfig, report: ReleaseAnalysis) -> Path:
    target = context.resolve_path(config.semantic.release_report_path)
    atomic_json_write(target, report)
    return target


def _owner_local_source_path(context: ModuleContext, source_path: Path) -> Path:
    resolved_source = source_path.resolve(strict=False)
    if _is_relative_to(resolved_source, context.module_root.resolve(strict=False)):
        return resolved_source
    payload = resolved_source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()[:24]
    suffix = resolved_source.suffix or ".json"
    target = context.state_dir / "semantic_release_incoming" / f"{resolved_source.stem}.{digest}{suffix}"
    atomic_bytes_write(target, payload)
    return target


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _release_fingerprint(payload: dict[str, Any]) -> str:
    value = str(payload.get("fingerprint") or "").strip()
    return value


def _require_release_bundle_path(path: Path) -> None:
    if path.exists() and path.is_dir():
        raise ValueError("Semantic Release Bundle muss auf eine .json-Datei zeigen, nicht auf ein Verzeichnis.")
    if path.suffix.casefold() != ".json":
        raise ValueError("Semantic Release Bundle muss auf eine .json-Datei zeigen.")


def _release_error(
    detail: Exception | str,
    path: Path,
    *,
    stage: str,
    fingerprint: str = "",
) -> ValueError:
    message = str(detail).strip() or "Semantic Release konnte nicht geladen werden."
    if "release_path=" in message:
        return ValueError(message)
    suffix_parts = [f"stage={stage}", f"release_path={path}"]
    if fingerprint:
        suffix_parts.append(f"release_fingerprint={fingerprint}")
    return ValueError(f"{message} [{', '.join(suffix_parts)}]")
