"""Soft routing and output naming policy for the processor."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_MAX_OUTPUT_SLUG_LENGTH = 120
_MAX_ASSET_KEY_LENGTH = 120
_MAX_OUTPUT_WRITE_ATTEMPTS = 64
_WINDOWS_PATH_BUDGET = 259
_OUTPUT_CLAIM_SUFFIX = ".claim"
_OUTPUT_SAFE_CHAR_RE = re.compile(r"[^A-Za-z0-9._-]+")
_KNOWN_OUTPUT_SUFFIXES = (".raw.json", ".json")


def normalize_output_seed(relative_path: str) -> str:
    normalized = (relative_path or "").replace("\\", "/").strip("/")
    return normalized or "extract"


def sanitize_output_fragment(value: str) -> str:
    slug = value.replace("/", "__")
    slug = _OUTPUT_SAFE_CHAR_RE.sub("_", slug).strip("._-")
    return slug or "extract"


def short_output_token(content_hash: str, fallback_seed: str) -> str:
    digest = (content_hash or "").strip().lower()
    if digest.startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    if re.fullmatch(r"[0-9a-f]{64}", digest):
        return digest[:8]
    seed = fallback_seed or "extract"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def build_asset_key(relative_path: str, content_hash: str) -> str:
    normalized = normalize_output_seed(relative_path)
    short_hash = short_output_token(content_hash, normalized)
    slug = sanitize_output_fragment(normalized)
    keep = max(16, _MAX_ASSET_KEY_LENGTH - len(short_hash) - 1)
    slug = slug[:keep].rstrip("._-") or "extract"
    return f"{slug}.{short_hash}"


def build_output_slug(relative_path: str, content_hash: str) -> str:
    normalized = normalize_output_seed(relative_path)
    slug = sanitize_output_fragment(normalized)
    short_hash = short_output_token(content_hash, normalized)
    if len(slug) > _MAX_OUTPUT_SLUG_LENGTH:
        keep = max(16, _MAX_OUTPUT_SLUG_LENGTH - len(short_hash) - 1)
        slug = f"{slug[:keep].rstrip('._-') or 'extract'}.{short_hash}"
    return slug


def iter_output_candidates(extracts_dir: Path, slug: str, page_suffix: str, short_hash: str):
    seen: set[Path] = set()
    first = extracts_dir / budget_output_name(
        extracts_dir,
        f"{slug}{page_suffix}.raw.json",
        reserved=len(_OUTPUT_CLAIM_SUFFIX),
    )
    if first not in seen:
        seen.add(first)
        yield first
    collision_slug = f"{slug}.{short_hash}"
    second = extracts_dir / budget_output_name(
        extracts_dir,
        f"{collision_slug}{page_suffix}.raw.json",
        reserved=len(_OUTPUT_CLAIM_SUFFIX),
    )
    if second not in seen:
        seen.add(second)
        yield second
    for attempt in range(1, _MAX_OUTPUT_WRITE_ATTEMPTS + 1):
        candidate = extracts_dir / budget_output_name(
            extracts_dir,
            f"{collision_slug}.{attempt:02d}{page_suffix}.raw.json",
            reserved=len(_OUTPUT_CLAIM_SUFFIX),
        )
        if candidate in seen:
            continue
        seen.add(candidate)
        yield candidate


def budget_output_name(parent: Path, preferred_name: str, *, reserved: int = 0) -> str:
    budget = max(_WINDOWS_PATH_BUDGET - max(reserved, 0), 64)
    safe_name = _OUTPUT_SAFE_CHAR_RE.sub("_", str(preferred_name or "").strip()).strip(" .") or "extract.raw.json"
    if _path_length(parent, safe_name) <= budget:
        return safe_name
    stem, suffixes = _split_output_suffixes(safe_name)
    digest = hashlib.sha1(safe_name.encode("utf-8")).hexdigest()[:8]
    truncated = stem or "extract"
    candidate = f"{truncated}.{digest}{suffixes}"
    while _path_length(parent, candidate) > budget and len(truncated) > 1:
        truncated = truncated[:-1]
        candidate = f"{truncated}.{digest}{suffixes}"
    return candidate


def budget_output_name_with_tail(parent: Path, preferred_stem: str, tail: str, suffix: str, *, reserved: int = 0) -> str:
    budget = max(_WINDOWS_PATH_BUDGET - max(reserved, 0), 64)
    safe_stem = _OUTPUT_SAFE_CHAR_RE.sub("_", str(preferred_stem or "").strip()).strip(" .") or "extract"
    safe_tail = str(tail or "").strip()
    safe_suffix = str(suffix or "").strip()
    preferred_name = f"{safe_stem}{safe_tail}{safe_suffix}"
    if _path_length(parent, preferred_name) <= budget:
        return preferred_name
    digest = hashlib.sha1(preferred_name.encode("utf-8")).hexdigest()[:8]
    truncated = safe_stem
    candidate = f"{truncated}.{digest}{safe_tail}{safe_suffix}"
    while _path_length(parent, candidate) > budget and len(truncated) > 1:
        truncated = truncated[:-1]
        candidate = f"{truncated}.{digest}{safe_tail}{safe_suffix}"
    return candidate


def page_raw_output_paths(raw_output_path: Path, total_pages: int) -> list[Path]:
    stem = raw_output_path.name
    suffix = ".raw.json"
    if stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return [
        raw_output_path.with_name(
            budget_output_name_with_tail(
                raw_output_path.parent,
                stem,
                f".p{page_number:03d}.of{total_pages:03d}",
                suffix,
                reserved=len(_OUTPUT_CLAIM_SUFFIX),
            )
        )
        for page_number in range(1, total_pages + 1)
    ]


def _split_output_suffixes(name: str) -> tuple[str, str]:
    lower_name = name.lower()
    for suffix in _KNOWN_OUTPUT_SUFFIXES:
        if lower_name.endswith(suffix):
            return name[: -len(suffix)] or "extract", name[-len(suffix) :]
    path = Path(name)
    if path.suffix:
        return path.stem or "extract", path.suffix
    return name or "extract", ""


def _path_length(parent: Path, name: str) -> int:
    return len(str(parent / name))
