from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .taxonomy_release_draft_schema import RELEASE_REQUIRED_KEYS, empty_draft, verification
from .taxonomy_release_draft_verification import master_core_signature


def find_release_candidates(artifact_root: str | Path) -> list[dict[str, Any]]:
    root = Path(artifact_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise ValueError(f"Artifact Tree nicht gefunden: {root}")
    candidates: dict[str, dict[str, Any]] = {}
    canonical_root = root / "Semantic Release" / "releases"
    for path in sorted(canonical_root.glob("*/release.json")) if canonical_root.is_dir() else []:
        _add_candidate(candidates, root, path, canonical=True)
    for path in sorted(root.rglob("release.json")):
        _add_candidate(candidates, root, path, canonical=False)
    return sorted(
        candidates.values(),
        key=lambda item: (not bool(item.get("canonical")), str(item.get("relative_path") or "").casefold()),
    )


def load_release_copy(artifact_root: str | Path, release_path: str | Path) -> dict[str, Any]:
    root = Path(artifact_root).expanduser().resolve(strict=False)
    path = Path(release_path).expanduser().resolve(strict=False)
    release = _read_release(path)
    _require_release_shape(release, label=str(path))
    origin_core_signature = master_core_signature(dict(release.get("master_taxonomy") or {}))
    draft = empty_draft()
    draft.update(
        {
            "artifact_root": str(root),
            "release_candidates": find_release_candidates(root) if root.is_dir() else [],
            "selected_release_path": str(path),
            "working_release_path": str(default_working_release_path({"artifact_root": str(root), "release": release})),
            "origin": {
                "artifact_root": str(root),
                "release_path": str(path),
                "release_id": str(release.get("release_id") or ""),
                "release_version": str(release.get("release_version") or ""),
                "fingerprint": str(release.get("fingerprint") or ""),
                "master_taxonomy_release_id": str(release.get("master_taxonomy_release_id") or ""),
                "master_core_signature": origin_core_signature,
            },
            "release": copy.deepcopy(release),
            "verification": verification("draft_loaded", warnings=["Working copy loaded; run Verify before applying it."]),
        }
    )
    return draft


def default_working_release_path(draft: dict[str, Any]) -> Path:
    release = draft.get("release") if isinstance(draft.get("release"), dict) else {}
    artifact_root = Path(str(draft.get("artifact_root") or ".")).expanduser().resolve(strict=False)
    release_id = _safe_path_segment(str(release.get("release_id") or "semantic_release.draft"))
    return artifact_root / "Semantic Release" / "drafts" / "edit_suite" / release_id / "release.json"


def working_release_path(draft: dict[str, Any]) -> Path:
    text = str(draft.get("working_release_path") or "").strip()
    return Path(text).expanduser().resolve(strict=False) if text else default_working_release_path(draft)


def _add_candidate(candidates: dict[str, dict[str, Any]], root: Path, path: Path, *, canonical: bool) -> None:
    if not path.is_file():
        return
    resolved = path.resolve(strict=False)
    key = str(resolved)
    if key in candidates and candidates[key].get("canonical"):
        return
    try:
        release = _read_release(resolved)
        _require_release_shape(release, label=str(resolved))
    except Exception:
        return
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        relative = resolved
    candidates[key] = {
        "path": str(resolved),
        "relative_path": str(relative),
        "release_id": str(release.get("release_id") or ""),
        "release_version": str(release.get("release_version") or ""),
        "fingerprint": str(release.get("fingerprint") or ""),
        "projection_count": len(release.get("projections") or []),
        "canonical": bool(canonical),
    }


def _read_release(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Semantic Release muss ein JSON-Objekt sein: {path}")
    return data


def _require_release_shape(release: dict[str, Any], *, label: str) -> None:
    missing = sorted(RELEASE_REQUIRED_KEYS - set(release))
    if missing:
        raise ValueError(f"{label} ist kein vollstaendiger Semantic Release: {', '.join(missing)}")


def _safe_path_segment(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value).strip())
    return safe.strip("._") or "semantic_release_draft"
