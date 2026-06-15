"""Asset adapter for page media-type detection and loading."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from .types import LoadedPageAsset

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
_BMP_SIGNATURE = b"BM"
_TIFF_SIGNATURES = (b"II*\x00", b"MM\x00*")


def _guess_media_type(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(str(path))
    return media_type or "application/octet-stream"


def resolve_page_media_type(path: Path, declared_media_type: str | None = None) -> str:
    candidates: list[str] = []
    if declared_media_type:
        candidates.append(str(declared_media_type).strip().lower())
    guessed = _guess_media_type(path).lower()
    if guessed not in candidates:
        candidates.append(guessed)
    for media_type in candidates:
        if media_type.startswith("image/"):
            return media_type
    return candidates[0] if candidates else "application/octet-stream"


def detect_image_media_type(data: bytes) -> str | None:
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    if data.startswith(_GIF_SIGNATURES):
        return "image/gif"
    if data.startswith(_BMP_SIGNATURE):
        return "image/bmp"
    if data.startswith(_TIFF_SIGNATURES):
        return "image/tiff"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _load_page_assets(
    request: dict[str, Any],
    *,
    asset_roots: tuple[Path, ...],
    max_page_assets: int,
    max_page_asset_bytes: int,
    max_request_asset_bytes: int,
) -> list[LoadedPageAsset]:
    source = request.get("source", {}) or {}
    context = request.get("context", {}) or {}
    pages = request.get("page_assets", []) or []
    if not isinstance(source, dict):
        raise ValueError("source muss ein Objekt sein")
    if not isinstance(context, dict):
        raise ValueError("context muss ein Objekt sein")
    if not isinstance(pages, list) or not pages:
        raise ValueError("page_assets ist leer")
    if len(pages) > max_page_assets:
        raise ValueError(f"page_assets ueberschreitet das Limit von {max_page_assets} Seiten")
    source_page_count = source.get("page_count")
    page_number = context.get("page_number")
    document_page_count = context.get("document_page_count")
    page_scoped_request = (
        len(pages) == 1
        and isinstance(page_number, int)
        and page_number > 0
        and isinstance(document_page_count, int)
        and document_page_count > 1
        and (
            not isinstance(source_page_count, int)
            or source_page_count == document_page_count
        )
    )
    if isinstance(source_page_count, int) and source_page_count != len(pages) and not page_scoped_request:
        raise ValueError("source.page_count stimmt nicht mit page_assets ueberein")

    normalized_roots = _normalize_asset_roots(asset_roots)
    total_bytes = 0
    loaded: list[LoadedPageAsset] = []
    expected_page = page_number if page_scoped_request else 1
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("page_assets enthaelt ungueltige Eintraege")
        page_no = page.get("page")
        page_path = _resolve_asset_path(str(page.get("path", "")), normalized_roots)
        media_type = resolve_page_media_type(page_path, page.get("media_type"))
        if page_no != expected_page:
            raise ValueError("Seitenbilder muessen in kanonischer Reihenfolge 1..N vorliegen")
        if normalized_roots and not _is_within_allowed_roots(page_path, normalized_roots):
            raise ValueError(f"Seitenbild liegt ausserhalb der erlaubten Wurzeln: {page_path}")
        if not page_path.is_file():
            raise ValueError(f"Seitenbild fehlt: {page_path}")
        size_bytes = page_path.stat().st_size
        if size_bytes > max_page_asset_bytes:
            raise ValueError(f"Seitenbild ueberschreitet das Limit von {max_page_asset_bytes} Bytes: {page_path}")
        total_bytes += size_bytes
        if total_bytes > max_request_asset_bytes:
            raise ValueError(f"page_assets ueberschreiten das Gesamtlimit von {max_request_asset_bytes} Bytes")
        try:
            data = page_path.read_bytes()
        except OSError as exc:
            raise ValueError(f"Seitenbild nicht lesbar: {page_path}") from exc
        if not data:
            raise ValueError(f"Seitenbild leer: {page_path}")
        detected_media_type = detect_image_media_type(data)
        if not media_type.startswith("image/") and detected_media_type is None:
            raise ValueError(f"Seitenbild ist kein Bild: {page_path} ({media_type})")
        if detected_media_type is None:
            raise ValueError(f"Seitenbild ist kein gueltiges Bild: {page_path} ({media_type})")
        loaded.append({"page": page_no, "path": page_path, "media_type": detected_media_type, "bytes": data})
        expected_page += 1
    return loaded


def load_page_assets(
    request: dict[str, Any],
    *,
    asset_roots: tuple[Path, ...] = (),
    max_page_assets: int = 15,
    max_page_asset_bytes: int = 12 * 1024 * 1024,
    max_request_asset_bytes: int = 40 * 1024 * 1024,
) -> list[LoadedPageAsset]:
    return _load_page_assets(
        request,
        asset_roots=asset_roots,
        max_page_assets=max_page_assets,
        max_page_asset_bytes=max_page_asset_bytes,
        max_request_asset_bytes=max_request_asset_bytes,
    )


def _normalize_asset_roots(asset_roots: tuple[Path, ...]) -> tuple[Path, ...]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for root in asset_roots:
        resolved_root = root.expanduser().resolve(strict=False)
        if resolved_root in seen:
            continue
        seen.add(resolved_root)
        roots.append(resolved_root)
    return tuple(roots)


def _resolve_asset_path(path_text: str, asset_roots: tuple[Path, ...]) -> Path:
    page_path = Path(path_text.strip()).expanduser()
    if not path_text.strip():
        return page_path
    if page_path.is_absolute() or not asset_roots:
        return page_path.resolve(strict=False)
    return (asset_roots[0] / page_path).resolve(strict=False)


def _is_within_allowed_roots(path: Path, asset_roots: tuple[Path, ...]) -> bool:
    for root in asset_roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


__all__ = ["detect_image_media_type", "load_page_assets", "resolve_page_media_type"]
