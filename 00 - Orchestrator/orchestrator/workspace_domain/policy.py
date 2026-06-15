from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_path(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve(strict=False))


def path_hash(value: str | Path) -> str:
    return "sha256:" + hashlib.sha256(canonical_path(value).encode("utf-8")).hexdigest()


def is_within(root: str | Path, candidate: str | Path) -> bool:
    try:
        Path(candidate).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
        return True
    except ValueError:
        return False


def canonical_folder_map(root: str | Path) -> dict[str, str]:
    root_path = Path(canonical_path(root))
    return {
        "artifact_root_path": str(root_path),
        "input_path": str(root_path / "Input"),
        "corpus_path": str(root_path / "Corpus"),
        "documents_path": str(root_path / "Documents"),
        "error_cases_path": str(root_path / "Error Cases"),
        "semantic_release_path": str(root_path / "Semantic Release"),
    }
