"""Persistent, secret-free request capture for Optimizer OCR calls."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .prompting import prompt_text
from .settings import LlmOcrSettings

REQUEST_DIR_ENV = "OPTIMIZER_OCR_REQUEST_DIR"


def persist_request(
    settings: LlmOcrSettings,
    assets: list[dict[str, str]],
    *,
    source_path: str | Path | None,
    endpoint: str,
    provider_payload: dict[str, Any],
    provider_route: str,
) -> Path | None:
    request_dir = _request_dir()
    if request_dir is None:
        return None
    payload = {
        "schema_version": "optimizer_ocr.request.v1",
        "captured_at": _utc_now_iso(),
        "source_path": str(source_path or ""),
        "provider_id": settings.provider_id,
        "provider_family": settings.provider_family,
        "provider_route": provider_route,
        "auth_mode": settings.auth_mode,
        "endpoint": endpoint,
        "model": settings.model,
        "max_output_tokens": settings.max_output_tokens,
        "timeout_seconds": settings.timeout_seconds,
        "response_format": "json_object",
        "prompt_text": prompt_text(len(assets), source_path=source_path),
        "image_payload_policy": "Image bytes are not duplicated here; use image_inputs paths and hashes.",
        "image_inputs": [_image_input(asset) for asset in assets],
        "provider_payload": _redact_image_data(provider_payload),
    }
    target = _next_request_path(request_dir)
    _atomic_json_write(target, payload)
    return target


def _request_dir() -> Path | None:
    text = str(os.environ.get(REQUEST_DIR_ENV) or "").strip()
    return Path(text) if text else None


def _image_input(asset: dict[str, str]) -> dict[str, Any]:
    path = Path(str(asset.get("path") or ""))
    return {
        "page_number": _int_text(asset.get("page_number")),
        "path": str(path),
        "media_type": str(asset.get("media_type") or ""),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        "sha256": _sha256_file(path) if path.is_file() else "",
        "detail": "high",
    }


def _redact_image_data(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("data:image/"):
            return "<image data omitted; see image_inputs>"
        return value
    if isinstance(value, list):
        return [_redact_image_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_image_data(item) for key, item in value.items()}
    return value


def _next_request_path(request_dir: Path) -> Path:
    request_dir.mkdir(parents=True, exist_ok=True)
    first = request_dir / "ocr.request.json"
    if not first.exists():
        return first
    for index in range(2, 10000):
        candidate = request_dir / f"ocr.{index:04d}.request.json"
        if not candidate.exists():
            return candidate
    raise OSError(f"Too many OCR request artifacts in {request_dir}")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem[:24]}.",
        suffix=f"{path.suffix}.tmp",
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(file_handle, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _replace_with_retry(source: Path, target: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.01 * (attempt + 1))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _int_text(value: object) -> int:
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
