"""Validation helpers for contract payloads."""
from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from ..models import OutputFilters

MAX_WORKER_COUNT = 8


def require_action(payload: dict) -> str:
    action = str(payload.get("action", "")).strip()
    if not action:
        raise ValueError("Aktion fehlt.")
    return action


def require_source_path(payload: dict, *, enforce_input_root: bool = True) -> Path:
    source_path = Path(str(payload["source_path"]))
    if not source_path.exists():
        raise FileNotFoundError(f"Quelldatei nicht gefunden: {source_path}")
    if not enforce_input_root:
        return source_path
    return _require_within_optional_root(source_path, payload, "input_root", "source_path")


def require_input_root(payload: dict) -> Path:
    input_root = Path(_required_path_text(payload, "input_root", "input_root fehlt."))
    if not input_root.exists() or not input_root.is_dir():
        raise FileNotFoundError(f"Input-Ordner nicht gefunden: {input_root}")
    return input_root


def require_output_root(payload: dict) -> Path:
    return Path(_required_path_text(payload, "output_root", "output_root fehlt."))


def require_session_root(payload: dict) -> Path:
    return Path(_required_path_text(payload, "session_root", "session_root fehlt."))


def require_raw_output_path(payload: dict) -> Path:
    path = Path(_required_path_text(payload, "raw_output_path", "raw_output_path fehlt."))
    return _require_within_optional_root(path, payload, "output_root", "raw_output_path")


def require_page_assets_dir(payload: dict) -> Path:
    path = Path(_required_path_text(payload, "page_assets_dir", "page_assets_dir fehlt."))
    return _require_within_optional_root(path, payload, "output_root", "page_assets_dir")


def optional_ocr_request_dir(payload: dict) -> Path | None:
    value = str(payload.get("ocr_request_dir", "")).strip()
    if not value:
        return None
    return _require_within_optional_root(Path(value), payload, "output_root", "ocr_request_dir")


def require_logical_source_path(payload: dict) -> str:
    normalized = normalize_logical_source_path(payload.get("logical_source_path"))
    if normalized is None:
        raise ValueError("logical_source_path muss ein relativer Pfad innerhalb der Pipeline sein.")
    return normalized


def require_runtime_policy_path(payload: dict) -> Path:
    runtime_policy_path = Path(_required_path_text(payload, "runtime_policy_path", "runtime_policy_path fehlt."))
    if not runtime_policy_path.exists() or not runtime_policy_path.is_file():
        raise FileNotFoundError(f"Runtime-Policy-Bundle nicht gefunden: {runtime_policy_path}")
    return runtime_policy_path


def require_mode(payload: dict, *, allowed: tuple[str, ...]) -> str:
    mode = str(payload.get("mode", "")).strip().lower()
    if mode not in allowed:
        joined = ", ".join(allowed)
        raise ValueError(f"mode muss einer von {joined} sein.")
    return mode


def require_filters(payload: dict) -> OutputFilters:
    raw_filters = payload.get("filters", {})
    if raw_filters is None:
        return OutputFilters()
    if not isinstance(raw_filters, dict):
        raise ValueError("filters muss ein JSON-Objekt sein.")
    return OutputFilters(
        format=str(raw_filters.get("format") or "").strip() or None,
        doc_type=str(raw_filters.get("doc_type") or "").strip() or None,
        max_size_mb=raw_filters.get("max_size_mb"),
        batch_size=raw_filters.get("batch_size", 0),
    )


def require_worker_count(payload: dict) -> int:
    try:
        worker_count = int(payload.get("worker_count", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("worker_count muss eine positive Ganzzahl sein.") from exc
    if worker_count < 1:
        raise ValueError("worker_count muss eine positive Ganzzahl sein.")
    if worker_count > MAX_WORKER_COUNT:
        raise ValueError(f"worker_count darf maximal {MAX_WORKER_COUNT} sein.")
    return worker_count


def use_processed_hashes(payload: dict) -> bool:
    raw_hash_tools = payload.get("hash_tools", {})
    if not isinstance(raw_hash_tools, dict):
        return False
    return bool(raw_hash_tools.get("use_processed_hashes"))


def required_healthcheck_dependencies(payload: dict) -> set[str]:
    raw_dependencies = payload.get("required_dependencies")
    if raw_dependencies is None or not isinstance(raw_dependencies, list):
        return {"pdf-pdfplumber"}
    names = {str(item).strip() for item in raw_dependencies if str(item).strip()}
    return names or {"pdf-pdfplumber"}


def normalize_logical_source_path(value: object) -> str | None:
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


def _required_path_text(payload: dict, key: str, message: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(message)
    return value


def _require_within_optional_root(path: Path, payload: dict, root_key: str, label: str) -> Path:
    root_text = str(payload.get(root_key, "")).strip()
    if not root_text:
        return path
    root = Path(root_text)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} muss innerhalb von {root_key} liegen.") from exc
    return path
