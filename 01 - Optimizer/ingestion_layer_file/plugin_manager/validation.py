"""Hard validation for plugin manifests and extractor payloads."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import zipfile

from ..models import ExtractResult, PluginManifest


def build_manifest(data: Any, fallback_name: str) -> PluginManifest:
    if not isinstance(data, dict):
        raise TypeError("plugin.json root payload must be an object")
    return PluginManifest(
        name=data.get("name", fallback_name),
        version=data.get("version", "0.0.0"),
        description=data.get("description", ""),
        author=data.get("author", ""),
        formats=data.get("formats", []),
        also_handles=data.get("also_handles", []),
        capabilities=data.get("capabilities", []),
        priority=data.get("priority", 0),
        python_version=data.get("python_version", ">=3.10"),
        system_dependencies=data.get("system_dependencies", []),
        config_schema=data.get("config_schema", {}),
        config=data.get("config", {}),
    )


def parse_result(data: Any) -> ExtractResult:
    if not isinstance(data, dict):
        return ExtractResult(status="error", errors=[f"Ungueltiges Plugin-Payload: {type(data).__name__}"])

    errors: list[str] = []
    raw_errors = data.get("errors", [])
    if isinstance(raw_errors, str):
        if raw_errors.strip():
            errors.append(raw_errors.strip())
    elif isinstance(raw_errors, list):
        for value in raw_errors:
            text = str(value).strip()
            if text:
                errors.append(text)
    elif raw_errors:
        text = str(raw_errors).strip()
        if text:
            errors.append(text)

    status = data.get("status", "error")
    if status != "success" and not errors:
        detail = str(data.get("message") or data.get("error") or "").strip()
        errors = [detail or "Extractor lieferte Fehlerstatus ohne Details"]

    metadata = data.get("metadata", {})
    blocks = data.get("blocks", [])
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(blocks, list):
        blocks = []

    return ExtractResult(
        status=status,
        blocks=blocks,
        metadata=metadata,
        errors=errors,
        processing_time_ms=data.get("processing_time_ms", 0),
        needs_ocr=bool(data.get("needs_ocr", False) or metadata.get("needs_ocr", False)),
    )


def validate_runtime_root(runtime_root: Path, name: str) -> None:
    if (runtime_root / "pyvenv.cfg").exists():
        raise FileNotFoundError(
            f"Extractor {name}: legacy venv-Runtime erkannt. Erwartet portable Runtime unter {runtime_root}"
        )
    stdlib_root = runtime_root / "Lib"
    if _has_portable_stdlib(stdlib_root) or _has_embedded_stdlib(runtime_root):
        return
    raise FileNotFoundError(
        f"Extractor {name}: portable oder embedded Standardbibliothek fehlt. Erwartet unter {runtime_root}"
    )


def _has_portable_stdlib(stdlib_root: Path) -> bool:
    return (stdlib_root / "os.py").exists() and (stdlib_root / "encodings" / "__init__.py").exists()


def _has_embedded_stdlib(runtime_root: Path) -> bool:
    if not any(runtime_root.glob("python*._pth")):
        return False
    for archive_path in runtime_root.glob("python*.zip"):
        try:
            with zipfile.ZipFile(archive_path) as archive:
                names = {name.replace("\\", "/").lower() for name in archive.namelist()}
        except (OSError, zipfile.BadZipFile):
            continue
        if any(name.endswith("/os.pyc") or name == "os.pyc" or name.endswith("/os.py") or name == "os.py" for name in names) and any(
            "encodings/__init__." in name or name == "encodings/__init__.pyc" or name == "encodings/__init__.py"
            for name in names
        ):
            return True
    return False
