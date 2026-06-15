"""Best-effort Outlook store bundle extraction helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import create_bundle_root, save_manifest
from .outlook_store_com import (
    _extract_outlook_attachments,
    _extract_via_outlook_com,
    _selftest_outlook_com_backend,
)
from .outlook_store_pypff import extract_via_pypff


def extract_outlook_store_bundle(
    input_path: str | Path,
    config: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any]]:
    source = Path(input_path)
    bundle_root = create_bundle_root("fom-store-")
    backend_name, messages = _extract_store_messages(bundle_root, source, dict(config or {}))
    manifest = {
        "bundle_version": 1,
        "container_kind": "outlook_store",
        "source_name": source.name,
        "backend": backend_name,
        "messages": messages,
    }
    save_manifest(bundle_root, manifest)
    return bundle_root, manifest


def selftest_outlook_store_backend() -> tuple[bool, str]:
    pypff_ok, pypff_detail = _selftest_pypff_backend()
    if pypff_ok:
        return True, pypff_detail
    com_ok, com_detail = _selftest_outlook_com_backend()
    if com_ok:
        return True, com_detail
    return False, f"{pypff_detail}; {com_detail}"


def _extract_store_messages(
    bundle_root: Path,
    source: Path,
    config: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    errors: list[str] = []
    for backend_name in _backend_order(config):
        try:
            if backend_name == "pypff":
                return backend_name, _extract_via_pypff(bundle_root, source)
            return backend_name, _extract_via_outlook_com(bundle_root, source)
        except Exception as exc:
            errors.append(f"{backend_name}: {exc}")
    raise RuntimeError("; ".join(errors) or f"Outlook-Store konnte nicht geoeffnet werden: {source}")


def _backend_order(config: dict[str, Any]) -> tuple[str, ...]:
    preferred = str(config.get("preferred_backend", "")).strip().lower()
    allow_com_fallback = _config_enabled(config.get("allow_com_fallback"), default=True)
    if preferred in {"com", "outlook_com"}:
        return ("outlook_com", "pypff") if allow_com_fallback else ("outlook_com",)
    if preferred == "pypff":
        return ("pypff", "outlook_com") if allow_com_fallback else ("pypff",)
    return ("pypff", "outlook_com") if allow_com_fallback else ("pypff",)


def _selftest_pypff_backend() -> tuple[bool, str]:
    try:
        _import_pypff()
        return True, "OK (pypff)"
    except Exception as exc:
        return False, f"pypff nicht verfuegbar: {exc}"


def _extract_via_pypff(bundle_root: Path, source: Path) -> list[dict[str, Any]]:
    return extract_via_pypff(bundle_root, source, import_pypff=_import_pypff)


def _import_pypff():
    import pypff

    return pypff


def _config_enabled(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
