"""Contract-visible path policy for optional page image persistence."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def candidate_dirs(
    file_path: str,
    file_name: str,
    content_hash: str,
    *,
    page_images_dir: str | Path | None,
    artifact_hint_path: Path | None,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    if page_images_dir:
        candidates.append(Path(page_images_dir))
    relative_dir = _relative_page_images_dir(file_path)
    suffix_dirs = _suffix_dirs(file_name, file_path, content_hash)
    for root in _candidate_roots(page_images_dir, artifact_hint_path):
        if relative_dir is not None:
            candidates.append(root / relative_dir)
        candidates.extend(root / suffix_dir for suffix_dir in suffix_dirs)
        candidates.extend(_hash_suffix_dirs(root, content_hash))
        candidates.extend(_file_name_prefix_dirs(root, file_name, file_path))
    return tuple(_unique_paths(candidates))


def _candidate_roots(page_images_dir: str | Path | None, artifact_hint_path: Path | None) -> tuple[Path, ...]:
    roots: list[Path] = []
    if page_images_dir:
        roots.append(Path(page_images_dir))
    artifact_root = _artifact_page_images_root(artifact_hint_path)
    if artifact_root is not None:
        roots.append(artifact_root)
    return tuple(_unique_paths(roots))


def _artifact_page_images_root(path: Path | None) -> Path | None:
    if path is None:
        return None
    parent_name = path.parent.name.lower()
    if parent_name in {"normalized", "structured"}:
        return path.parent.parent / "page_images"
    return None


def _relative_page_images_dir(file_path: str) -> Path | None:
    raw_text = str(file_path or "").strip().replace("\\", "/")
    if not raw_text:
        return None
    parts = PurePosixPath(raw_text).parts
    if "page_images" not in parts:
        return None
    relative = PurePosixPath(*parts[parts.index("page_images") + 1 :])
    return Path(relative.parent if relative.suffix else relative)


def _suffix_dirs(file_name: str, file_path: str, content_hash: str) -> tuple[Path, ...]:
    file_leaf = str(file_name or "").strip() or Path(str(file_path or "")).name
    hash_text = str(content_hash or "").strip().removeprefix("sha256:")
    if not file_leaf or len(hash_text) < 8:
        return ()
    names = [file_leaf]
    sanitized = file_leaf.replace(" ", "_")
    if sanitized != file_leaf:
        names.append(sanitized)
    return tuple(Path(f"{name}.{hash_text[:8]}") for name in names)


def _hash_suffix_dirs(root: Path, content_hash: str) -> tuple[Path, ...]:
    hash_text = str(content_hash or "").strip().removeprefix("sha256:")
    if len(hash_text) < 8 or not root.is_dir():
        return ()
    suffix = f".{hash_text[:8]}".lower()
    try:
        return tuple(path for path in root.iterdir() if path.is_dir() and path.name.lower().endswith(suffix))
    except OSError:
        return ()


def _file_name_prefix_dirs(root: Path, file_name: str, file_path: str) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    file_leaf = str(file_name or "").strip() or Path(str(file_path or "")).name
    if not file_leaf:
        return ()
    prefixes = {f"{file_leaf}.".casefold()}
    sanitized = file_leaf.replace(" ", "_")
    if sanitized != file_leaf:
        prefixes.add(f"{sanitized}.".casefold())
    try:
        return tuple(
            path
            for path in root.iterdir()
            if path.is_dir() and any(path.name.casefold().startswith(prefix) for prefix in prefixes)
        )
    except OSError:
        return ()


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


__all__ = ["IMAGE_EXTENSIONS", "candidate_dirs"]
