"""Filesystem adapter for optional page image discovery and byte loading."""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path

from .page_image_policy import candidate_dirs

_PAGE_PATTERN = re.compile(r"^page_(\d{3})\.(png|jpe?g)$", re.IGNORECASE)


def load_page_images(
    document: dict[str, object],
    *,
    page_images_dir: str | Path | None,
    artifact_hint_path: Path | None,
    max_image_bytes: int | None = 10485760,
    max_total_bytes: int | None = 104857600,
) -> tuple[list[dict[str, object]], list[str]]:
    page_count = _page_count(document.get("page_count"))
    source_page = _page_count(document.get("source_page"))
    expected_page_count = 1 if source_page else page_count
    warnings: list[str] = []
    page_images: list[dict[str, object]] = []
    seen_pages: set[int] = set()
    total_bytes = 0
    for image_dir in candidate_dirs(
        str(document.get("file_path") or ""),
        str(document.get("file_name") or ""),
        str(document.get("content_hash") or ""),
        page_images_dir=page_images_dir,
        artifact_hint_path=artifact_hint_path,
    ):
        if not image_dir.is_dir():
            continue
        for image_path in sorted(image_dir.iterdir()):
            page = _page_number(image_path)
            if page is None or page in seen_pages:
                continue
            if source_page and page != source_page:
                continue
            if not source_page and page_count and page > page_count:
                continue
            try:
                byte_size = image_path.stat().st_size
            except OSError as exc:
                warnings.append(f"Seitenbild {image_path} konnte nicht gelesen werden: {exc}")
                continue
            if max_image_bytes is not None and max_image_bytes > 0 and byte_size > max_image_bytes:
                warnings.append(f"Seitenbild {image_path} ueberschreitet das Einzelbild-Limit von {max_image_bytes} Bytes.")
                continue
            if max_total_bytes is not None and max_total_bytes > 0 and total_bytes + byte_size > max_total_bytes:
                warnings.append(f"Seitenbild {image_path} wuerde das Gesamtlimit von {max_total_bytes} Bytes ueberschreiten.")
                continue
            try:
                blob = image_path.read_bytes()
            except OSError as exc:
                warnings.append(f"Seitenbild {image_path} konnte nicht gelesen werden: {exc}")
                continue
            if max_image_bytes is not None and max_image_bytes > 0 and len(blob) > max_image_bytes:
                warnings.append(f"Seitenbild {image_path} ueberschreitet das Einzelbild-Limit von {max_image_bytes} Bytes.")
                continue
            if max_total_bytes is not None and max_total_bytes > 0 and total_bytes + len(blob) > max_total_bytes:
                warnings.append(f"Seitenbild {image_path} wuerde das Gesamtlimit von {max_total_bytes} Bytes ueberschreiten.")
                continue
            seen_pages.add(page)
            total_bytes += len(blob)
            page_images.append(
                {
                    "page": page,
                    "content_type": _content_type(image_path),
                    "byte_size": len(blob),
                    "image_sha256": hashlib.sha256(blob).hexdigest(),
                    "image_blob": blob,
                }
            )
    if not page_images:
        warnings.append("Keine Seitenbilder gefunden.")
    elif expected_page_count and len(page_images) < expected_page_count:
        warnings.append(
            f"Nur {len(page_images)} von {expected_page_count} erwarteten Seitenbildern gefunden."
        )
    return page_images, warnings


def _page_count(value: object) -> int:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return count if count > 0 else 0


def _page_number(path: Path) -> int | None:
    match = _PAGE_PATTERN.match(path.name)
    if not match:
        return None
    page = int(match.group(1))
    return page if page > 0 else None


def _content_type(path: Path) -> str:
    guessed, _encoding = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


__all__ = ["load_page_images"]
