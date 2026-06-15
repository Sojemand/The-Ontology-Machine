from __future__ import annotations

from pathlib import Path
from typing import Sequence

from semantic_control_kernel.repository.paths import path_hash
from semantic_control_kernel.workflows.merge.source_registry_errors import MergeSourceResolutionError


def unique_paths(paths: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in paths:
        text = str(value or "").strip()
        if not text:
            continue
        resolved = str(Path(text).resolve(strict=False))
        key = path_hash(resolved)
        if key in seen:
            continue
        seen.add(key)
        unique.append(resolved)
    return tuple(unique)


def source_paths_from_input(value: str) -> dict[str, str]:
    path = Path(value).resolve(strict=False)
    if path.is_file():
        root = artifact_root_for_database_path(path)
        return {"artifact_root_path": str(root), "database_path": str(path)}
    if not path.exists() or not path.is_dir():
        raise MergeSourceResolutionError(f"Source Artifact Tree folder does not exist: {value}")
    roots = artifact_tree_roots_below(path)
    if not roots:
        raise MergeSourceResolutionError(f"No Artifact Tree root with a Corpus folder was found below: {value}")
    if len(roots) > 1:
        raise MergeSourceResolutionError(
            f"Source folder contains multiple Artifact Tree roots; select each root explicitly: {value}"
        )
    root = roots[0]
    return {"artifact_root_path": str(root), "database_path": str(single_database_in_artifact_root(root))}


def artifact_tree_roots_below(path: Path) -> list[Path]:
    if looks_like_artifact_root(path):
        return [path]
    roots: list[Path] = []
    for corpus_dir in sorted(path.rglob("Corpus")):
        if not corpus_dir.is_dir():
            continue
        candidate = corpus_dir.parent
        if looks_like_artifact_root(candidate):
            roots.append(candidate)
            if len(roots) > 1:
                return roots
    return roots


def looks_like_artifact_root(path: Path) -> bool:
    expected = ("Input", "Corpus", "Semantic Release", "Documents", "Error Cases")
    return path.is_dir() and all((path / name).is_dir() for name in expected)


def single_database_in_artifact_root(root: Path) -> Path:
    preferred = root / "Corpus" / "corpus.db"
    if preferred.is_file():
        return preferred.resolve(strict=False)
    corpus = root / "Corpus"
    candidates = sorted(path.resolve(strict=False) for path in corpus.rglob("*.db") if path.is_file())
    if not candidates:
        raise MergeSourceResolutionError(f"Artifact Tree has no Corpus database: {root}")
    if len(candidates) > 1:
        raise MergeSourceResolutionError(f"Artifact Tree Corpus folder contains multiple databases: {root}")
    return candidates[0]


def artifact_root_for_database_path(database_path: Path) -> Path:
    corpus = database_path.parent
    root = corpus.parent
    if corpus.name != "Corpus" or not looks_like_artifact_root(root):
        raise MergeSourceResolutionError(
            f"Source database path is not inside an Artifact Tree Corpus folder: {database_path}"
        )
    return root.resolve(strict=False)
