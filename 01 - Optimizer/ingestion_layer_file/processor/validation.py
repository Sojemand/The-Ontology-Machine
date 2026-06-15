"""Hard validation boundaries for processor inputs and hashes."""
from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath, PureWindowsPath

from ..input_catalog import InputCatalog
from ..models import FileTooLargeError, InputFileNotFoundError, PluginError, UnsupportedFormatError

logger = logging.getLogger(__name__)


def validate_batch_context(processor) -> None:
    if not processor._requested_output_dir or not processor._input_catalog:
        raise ValueError("process() erfordert output_dir und input_catalog")


def ensure_existing_file(file_path: Path) -> None:
    if not file_path.exists():
        raise InputFileNotFoundError(f"Datei nicht gefunden: {file_path}")


def ensure_file_size(size: int, max_file_size_mb: int) -> None:
    max_bytes = max_file_size_mb * 1024 * 1024
    if size > max_bytes:
        raise FileTooLargeError(f"Datei zu gross: {size} bytes")


def ensure_plugin_name(plugin_name: str | None, ext: str) -> str:
    if not plugin_name:
        raise UnsupportedFormatError(f"Kein Plugin fuer Format: {ext}")
    return plugin_name


def ensure_success_result(plugin_name: str, result) -> None:
    if result.status == "success":
        return
    details = [str(value).strip() for value in (result.errors or []) if str(value).strip()]
    detail = "; ".join(details) if details else "Plugin lieferte Fehlerstatus ohne Details"
    raise PluginError(plugin_name, detail)


def normalize_content_hash(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    return InputCatalog._normalize_hash_value(value)


def resolve_content_hash(processor, file_path: Path, candidate_hash: str | None = None) -> str:
    normalized = normalize_content_hash(candidate_hash)
    if normalized is not None:
        return normalized
    if candidate_hash:
        logger.warning("Ungueltiger content_hash fuer %s, berechne Datei-Hash neu", file_path)
    recomputed = normalize_content_hash(processor._compute_hash(file_path))
    if recomputed is None:
        raise OSError(f"Hash-Berechnung fehlgeschlagen fuer {file_path}")
    return recomputed


def archive_dir_name(content_hash: str) -> str:
    return content_hash.split(":", 1)[1][:16]


def require_vision_output_dir(file_path: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        raise ValueError(f"Vision-Dokumente erfordern write_output=True und ein output_dir: {file_path}")
    return output_dir


def validate_explicit_single_file_targets(
    *,
    write_output: bool,
    output_dir: Path | None,
    raw_output_path: Path | None,
    page_assets_dir: Path | None,
    logical_source_path: str | None,
) -> str | None:
    uses_explicit_targets = raw_output_path is not None or page_assets_dir is not None or logical_source_path is not None
    if not uses_explicit_targets:
        return None
    if not write_output:
        raise ValueError("Explizite Single-File-Zielpfade erfordern write_output=True.")
    if output_dir is not None:
        raise ValueError("Explizite Single-File-Zielpfade sind nicht mit output_dir kombinierbar.")
    if raw_output_path is None:
        raise ValueError("raw_output_path fehlt fuer explizite Single-File-Zielpfade.")
    if page_assets_dir is None:
        raise ValueError("page_assets_dir fehlt fuer explizite Single-File-Zielpfade.")
    normalized = normalize_logical_source_path(logical_source_path)
    if normalized is None:
        raise ValueError("logical_source_path muss ein relativer Pfad innerhalb der Pipeline sein.")
    return normalized


def normalize_logical_source_path(value: str | None) -> str | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    windows_path = PureWindowsPath(raw_value)
    posix_text = raw_value.replace("\\", "/")
    posix_path = PurePosixPath(posix_text)
    if windows_path.is_absolute() or windows_path.drive or windows_path.root or posix_path.is_absolute():
        return None
    parts: list[str] = []
    for part in posix_text.split("/"):
        normalized = part.strip()
        if not normalized or normalized == ".":
            continue
        if normalized == ".." or ":" in normalized:
            return None
        parts.append(normalized)
    return "/".join(parts) if parts else None
